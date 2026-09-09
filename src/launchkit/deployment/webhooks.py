"""Official HMAC-SHA1 verification and correlation for Vercel webhooks."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from launchkit.builds.service import safe_provider_url
from launchkit.builds.webhooks import delivery_identifier
from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, DomainError
from launchkit.core.models import AliasedModel
from launchkit.deployment.state import transition_deployment
from launchkit.persistence.repositories import PersistenceRepository

VERCEL_DEPLOYMENT_EVENTS = frozenset(
    {
        "deployment.created",
        "deployment.ready",
        "deployment.succeeded",
        "deployment.error",
        "deployment.canceled",
        "deployment.cancelled",
    }
)


class VercelWebhookAccessError(DomainError):
    """Raised when the official Vercel signature is invalid."""


class VercelWebhookPayloadError(DomainError):
    """Raised when a signed payload cannot be parsed safely."""


class VercelWebhookReceipt(AliasedModel):
    status: str
    duplicate: bool = False
    correlated: bool = False


class VercelWebhookService:
    def __init__(self, repository: PersistenceRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def receive(self, raw_body: bytes, signature: str | None) -> VercelWebhookReceipt:
        secret = (
            self._settings.vercel_webhook_secret.get_secret_value()
            if self._settings.vercel_webhook_secret
            else ""
        )
        if not secret:
            raise ConfigurationError("Vercel webhook secret is not configured")
        expected = hmac.new(secret.encode(), raw_body, hashlib.sha1).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            raise VercelWebhookAccessError("Invalid Vercel webhook signature")
        if len(raw_body) > self._settings.webhook_max_bytes:
            raise VercelWebhookPayloadError("Webhook payload is too large")
        try:
            payload: Any = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VercelWebhookPayloadError("Invalid webhook JSON") from exc
        if not isinstance(payload, Mapping):
            raise VercelWebhookPayloadError("Invalid webhook payload")
        body = dict(payload)
        event_type = str(payload.get("type") or "unknown")
        delivery_key = delivery_identifier(payload, raw_body)
        if (
            await self._repository.get_webhook_delivery(
                provider="vercel", delivery_key=delivery_key
            )
            is not None
        ):
            return VercelWebhookReceipt(status="accepted", duplicate=True)
        delivery = await self._repository.add_webhook_delivery(
            provider="vercel",
            delivery_key=delivery_key,
            event_type=event_type,
            payload=body,
        )
        if event_type not in VERCEL_DEPLOYMENT_EVENTS:
            delivery.status = "ignored"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            return VercelWebhookReceipt(status="ignored")
        provider_id = extract_deployment_id(payload)
        if provider_id is None:
            delivery.status = "invalid"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            raise VercelWebhookPayloadError("Webhook contains no deployment ID")
        deployment = await self._repository.find_deployment_by_provider_reference(
            provider="vercel",
            reference_type="deployment_id",
            reference_value=provider_id,
        )
        if deployment is None:
            delivery.status = "unknown_resource"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            return VercelWebhookReceipt(status="ignored")
        delivery.resource_type = "deployment"
        delivery.resource_id = deployment.id
        delivery.processed_at = datetime.now(UTC)
        if event_type in {"deployment.error"} and deployment.status not in {
            "failed",
            "cancelled",
            "completed",
        }:
            await transition_deployment(
                self._repository,
                deployment,
                "failed",
                message="The Vercel deployment failed",
            )
            deployment.completed_at = datetime.now(UTC)
        elif event_type in {
            "deployment.canceled",
            "deployment.cancelled",
        } and deployment.status not in {
            "failed",
            "cancelled",
            "completed",
        }:
            await transition_deployment(
                self._repository,
                deployment,
                "cancelled",
                message="The Vercel deployment was cancelled",
            )
            deployment.completed_at = datetime.now(UTC)
        else:
            url = extract_deployment_url(payload)
            if url:
                deployment.live_url = url
        delivery.status = "processed"
        await self._repository.commit()
        return VercelWebhookReceipt(status="accepted", correlated=True)


def extract_deployment_id(payload: Mapping[str, Any]) -> str | None:
    nested = payload.get("payload")
    if isinstance(nested, Mapping):
        deployment = nested.get("deployment")
        if isinstance(deployment, Mapping) and isinstance(deployment.get("id"), str):
            return str(deployment["id"])
        candidate = nested.get("deploymentId")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def extract_deployment_url(payload: Mapping[str, Any]) -> str | None:
    nested = payload.get("payload")
    if not isinstance(nested, Mapping):
        return None
    deployment = nested.get("deployment")
    if not isinstance(deployment, Mapping):
        return None
    candidate = deployment.get("url")
    if not isinstance(candidate, str) or not candidate:
        return None
    value = candidate if "://" in candidate else f"https://{candidate}"
    return safe_provider_url(value)
