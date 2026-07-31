"""Direct verification and correlation tests for signed Vercel webhooks."""

import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError
from launchkit.deployment.webhooks import (
    VercelWebhookAccessError,
    VercelWebhookPayloadError,
    VercelWebhookReceipt,
    VercelWebhookService,
    extract_deployment_id,
    extract_deployment_url,
)
from launchkit.persistence.models import DeploymentRecord
from launchkit.persistence.repositories import PersistenceRepository


class VercelWebhookRepositoryStub:
    def __init__(self) -> None:
        self.deliveries: dict[str, Any] = {}
        self.deployment: DeploymentRecord | None = None
        self.events: list[dict[str, Any]] = []
        self.commits = 0

    async def get_webhook_delivery(self, **values: str) -> Any | None:
        return self.deliveries.get(values["delivery_key"])

    async def add_webhook_delivery(self, **values: Any) -> Any:
        delivery = SimpleNamespace(
            **values,
            status="received",
            processed_at=None,
            resource_type=None,
            resource_id=None,
        )
        self.deliveries[values["delivery_key"]] = delivery
        return delivery

    async def find_deployment_by_provider_reference(self, **values: str) -> DeploymentRecord | None:
        assert values["reference_value"].startswith("dpl_")
        return self.deployment

    async def add_status_event(self, **event: Any) -> None:
        self.events.append(event)

    async def commit(self) -> None:
        self.commits += 1


def webhook_service(
    repository: VercelWebhookRepositoryStub,
    *,
    secret: str | None = "secret",
    max_bytes: int = 1024,
) -> VercelWebhookService:
    return VercelWebhookService(
        cast(PersistenceRepository, repository),
        Settings(
            environment="test",
            vercel_webhook_secret=secret,
            webhook_max_bytes=max_bytes,
        ),
    )


def raw_payload(payload: object) -> tuple[bytes, str]:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return raw, hmac.new(b"secret", raw, hashlib.sha1).hexdigest()


def receive(repository: VercelWebhookRepositoryStub, payload: object) -> VercelWebhookReceipt:
    raw, signature = raw_payload(payload)
    return asyncio.run(webhook_service(repository).receive(raw, signature))


def deployment(status: str = "ready_to_claim") -> DeploymentRecord:
    now = datetime.now(UTC)
    return DeploymentRecord(
        id="deployment-1",
        build_id="build-1",
        status=status,
        public_message="Ready",
        created_at=now,
        updated_at=now,
    )


def test_receive_rejects_configuration_signature_size_and_json() -> None:
    repository = VercelWebhookRepositoryStub()
    with pytest.raises(ConfigurationError, match="not configured"):
        asyncio.run(webhook_service(repository, secret=None).receive(b"{}", "signature"))
    with pytest.raises(VercelWebhookAccessError, match="signature"):
        asyncio.run(webhook_service(repository).receive(b"{}", "wrong"))

    oversized = b"x" * 1025
    signature = hmac.new(b"secret", oversized, hashlib.sha1).hexdigest()
    with pytest.raises(VercelWebhookPayloadError, match="too large"):
        asyncio.run(webhook_service(repository).receive(oversized, signature))

    malformed = b"{"
    signature = hmac.new(b"secret", malformed, hashlib.sha1).hexdigest()
    with pytest.raises(VercelWebhookPayloadError, match="Invalid webhook JSON"):
        asyncio.run(webhook_service(repository).receive(malformed, signature))
    with pytest.raises(VercelWebhookPayloadError, match="Invalid webhook payload"):
        receive(repository, ["not", "object"])


def test_receive_ignores_events_and_deduplicates() -> None:
    repository = VercelWebhookRepositoryStub()
    payload = {"id": "event-1", "type": "project.created", "payload": {}}
    ignored = receive(repository, payload)
    duplicate = receive(repository, payload)
    assert ignored.status == "ignored"
    assert duplicate.duplicate is True


def test_receive_handles_missing_unknown_and_correlated_resources() -> None:
    repository = VercelWebhookRepositoryStub()
    with pytest.raises(VercelWebhookPayloadError, match="no deployment ID"):
        receive(
            repository,
            {"id": "missing", "type": "deployment.error", "payload": {}},
        )
    assert repository.deliveries["missing"].status == "invalid"

    unknown = receive(
        repository,
        {
            "id": "unknown",
            "type": "deployment.error",
            "payload": {"deployment": {"id": "dpl_unknown"}},
        },
    )
    assert unknown.status == "ignored"

    repository.deployment = deployment()
    ready = receive(
        repository,
        {
            "id": "ready",
            "type": "deployment.succeeded",
            "payload": {"deployment": {"id": "dpl_ready", "url": "site.vercel.app"}},
        },
    )
    assert ready.correlated is True
    assert repository.deployment.live_url == "https://site.vercel.app"

    failed = receive(
        repository,
        {
            "id": "failed",
            "type": "deployment.error",
            "payload": {"deployment": {"id": "dpl_failed"}},
        },
    )
    assert failed.correlated is True
    assert repository.deployment.status == "failed"


def test_receive_cancels_active_deployments_and_helpers_reject_unsafe_values() -> None:
    repository = VercelWebhookRepositoryStub()
    repository.deployment = deployment("building")
    receipt = receive(
        repository,
        {
            "id": "cancelled",
            "type": "deployment.cancelled",
            "payload": {"deploymentId": "dpl_cancelled"},
        },
    )
    assert receipt.correlated is True
    assert repository.deployment.status == "cancelled"
    assert extract_deployment_id({"payload": {"deploymentId": "dpl_direct"}}) == "dpl_direct"
    assert extract_deployment_id({}) is None
    assert extract_deployment_url({}) is None
    assert extract_deployment_url({"payload": {"deployment": {"url": "http://unsafe"}}}) is None
