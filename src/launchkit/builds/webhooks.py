"""Secure fallback handling for unsigned v0 hook deliveries."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from launchkit.builds.state import TERMINAL_BUILD_STATUSES
from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, DomainError
from launchkit.core.models import AliasedModel
from launchkit.persistence.repositories import PersistenceRepository


class WebhookAccessError(DomainError):
    """Raised when a webhook path token is absent or incorrect."""


class WebhookPayloadError(DomainError):
    """Raised when a hook delivery cannot be parsed safely."""


class WebhookReceipt(AliasedModel):
    status: str
    duplicate: bool = False
    correlated: bool = False


class V0WebhookService:
    def __init__(self, repository: PersistenceRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def receive(self, token: str, raw_body: bytes) -> WebhookReceipt:
        expected = (
            self._settings.v0_webhook_token.get_secret_value()
            if self._settings.v0_webhook_token
            else ""
        )
        if not expected:
            raise ConfigurationError("v0 webhook token is not configured")
        if not hmac.compare_digest(token, expected):
            raise WebhookAccessError("Webhook not found")
        if len(raw_body) > self._settings.webhook_max_bytes:
            raise WebhookPayloadError("Webhook payload is too large")
        try:
            payload: Any = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebhookPayloadError("Invalid webhook JSON") from exc
        if not isinstance(payload, Mapping):
            raise WebhookPayloadError("Invalid webhook payload")
        body = dict(payload)
        event_type = str(
            payload.get("type") or payload.get("event") or payload.get("eventType") or "unknown"
        )
        delivery_key = delivery_identifier(payload, raw_body)
        if (
            await self._repository.get_webhook_delivery(provider="v0", delivery_key=delivery_key)
            is not None
        ):
            return WebhookReceipt(status="accepted", duplicate=True)
        delivery = await self._repository.add_webhook_delivery(
            provider="v0",
            delivery_key=delivery_key,
            event_type=event_type,
            payload=body,
        )
        if event_type != "message.finished":
            delivery.status = "ignored"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            return WebhookReceipt(status="ignored")
        chat_id = extract_chat_id(payload)
        if chat_id is None:
            delivery.status = "invalid"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            raise WebhookPayloadError("Webhook contains no chat ID")
        build = await self._repository.find_build_by_provider_reference(
            provider="v0", reference_type="chat_id", reference_value=chat_id
        )
        if build is None:
            delivery.status = "unknown_resource"
            delivery.processed_at = datetime.now(UTC)
            await self._repository.commit()
            return WebhookReceipt(status="ignored")
        delivery.resource_type = "build"
        delivery.resource_id = build.id
        delivery.processed_at = datetime.now(UTC)
        if build.status in TERMINAL_BUILD_STATUSES:
            delivery.status = "ignored_terminal"
            await self._repository.commit()
            return WebhookReceipt(status="accepted", correlated=True)
        delivery.status = "queued_reconciliation"
        await self._repository.enqueue_job("build.reconcile", {"buildId": build.id})
        await self._repository.commit()
        return WebhookReceipt(status="accepted", correlated=True)


def delivery_identifier(payload: Mapping[str, Any], raw_body: bytes) -> str:
    candidate = payload.get("id") or payload.get("deliveryId") or payload.get("eventId")
    return str(candidate)[:128] if candidate else hashlib.sha256(raw_body).hexdigest()


def extract_chat_id(value: object, depth: int = 0) -> str | None:
    if depth > 5:
        return None
    if isinstance(value, Mapping):
        for key in ("chatId", "chat_id"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate:
                return candidate
        chat = value.get("chat")
        if isinstance(chat, Mapping):
            candidate = chat.get("id")
            if isinstance(candidate, str) and candidate:
                return candidate
        for nested in value.values():
            candidate = extract_chat_id(nested, depth + 1)
            if candidate:
                return candidate
    elif isinstance(value, list):
        for nested in value:
            candidate = extract_chat_id(nested, depth + 1)
            if candidate:
                return candidate
    return None
