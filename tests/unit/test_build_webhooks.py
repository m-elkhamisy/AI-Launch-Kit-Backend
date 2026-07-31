"""v0 webhook validation, deduplication, and build correlation."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from launchkit.builds.webhooks import (
    V0WebhookService,
    WebhookAccessError,
    WebhookPayloadError,
    WebhookReceipt,
    delivery_identifier,
    extract_chat_id,
)
from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError
from launchkit.persistence.models import BuildRecord
from launchkit.persistence.repositories import PersistenceRepository


class WebhookRepositoryStub:
    def __init__(self) -> None:
        self.deliveries: dict[str, Any] = {}
        self.build: BuildRecord | None = None
        self.jobs: list[tuple[str, dict[str, str]]] = []
        self.commits = 0

    async def get_webhook_delivery(self, *, provider: str, delivery_key: str) -> Any | None:
        assert provider == "v0"
        return self.deliveries.get(delivery_key)

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

    async def find_build_by_provider_reference(self, **values: str) -> BuildRecord | None:
        assert values == {
            "provider": "v0",
            "reference_type": "chat_id",
            "reference_value": "chat-1",
        }
        return self.build

    async def enqueue_job(self, kind: str, payload: dict[str, str]) -> None:
        self.jobs.append((kind, payload))

    async def commit(self) -> None:
        self.commits += 1


def webhook_service(
    repository: WebhookRepositoryStub, *, token: str | None = "secret", max_bytes: int = 1024
) -> V0WebhookService:
    settings = Settings(environment="test", v0_webhook_token=token, webhook_max_bytes=max_bytes)
    return V0WebhookService(cast(PersistenceRepository, repository), settings)


def receive(
    repository: WebhookRepositoryStub,
    payload: object,
    *,
    token: str = "secret",
) -> WebhookReceipt:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return asyncio.run(webhook_service(repository).receive(token, raw))


def build(status: str) -> BuildRecord:
    now = datetime.now(UTC)
    return BuildRecord(
        id="build-1",
        project_id="project-1",
        provider="v0",
        status=status,
        stage=status,
        message=status,
        warnings=[],
        created_at=now,
        updated_at=now,
    )


def test_receive_rejects_configuration_access_size_and_json_errors() -> None:
    repository = WebhookRepositoryStub()
    with pytest.raises(ConfigurationError, match="not configured"):
        asyncio.run(webhook_service(repository, token=None).receive("secret", b"{}"))
    with pytest.raises(WebhookAccessError, match="not found"):
        asyncio.run(webhook_service(repository).receive("wrong", b"{}"))
    with pytest.raises(WebhookPayloadError, match="too large"):
        asyncio.run(webhook_service(repository).receive("secret", b"x" * 1025))
    with pytest.raises(WebhookPayloadError, match="Invalid webhook JSON"):
        asyncio.run(webhook_service(repository).receive("secret", b"{"))
    with pytest.raises(WebhookPayloadError, match="Invalid webhook payload"):
        receive(repository, ["not", "an", "object"])


def test_receive_ignores_other_events_and_deduplicates_delivery_ids() -> None:
    repository = WebhookRepositoryStub()
    payload = {"id": "delivery-1", "type": "message.created", "data": {}}
    ignored = receive(repository, payload)
    duplicate = receive(repository, payload)

    assert ignored.status == "ignored"
    assert duplicate.duplicate is True
    assert repository.deliveries["delivery-1"].status == "ignored"
    assert repository.commits == 1


def test_receive_marks_missing_and_unknown_chat_ids() -> None:
    repository = WebhookRepositoryStub()
    with pytest.raises(WebhookPayloadError, match="no chat ID"):
        receive(repository, {"id": "missing", "type": "message.finished"})
    assert repository.deliveries["missing"].status == "invalid"

    unknown = receive(
        repository,
        {"id": "unknown", "event": "message.finished", "data": {"chatId": "chat-1"}},
    )
    assert unknown.status == "ignored"
    assert repository.deliveries["unknown"].status == "unknown_resource"


def test_receive_correlates_terminal_and_active_builds() -> None:
    repository = WebhookRepositoryStub()
    repository.build = build("completed")
    terminal = receive(
        repository,
        {"deliveryId": "terminal", "eventType": "message.finished", "chat": {"id": "chat-1"}},
    )
    assert terminal.correlated is True
    assert repository.deliveries["terminal"].status == "ignored_terminal"

    repository.build = build("running")
    active = receive(
        repository,
        {"eventId": "active", "type": "message.finished", "items": [{"chat_id": "chat-1"}]},
    )
    assert active.correlated is True
    assert repository.deliveries["active"].resource_id == "build-1"
    assert repository.jobs == [("build.reconcile", {"buildId": "build-1"})]


def test_delivery_identifier_and_recursive_chat_extraction() -> None:
    assert delivery_identifier({"id": "x" * 200}, b"body") == "x" * 128
    assert len(delivery_identifier({}, b"body")) == 64
    assert extract_chat_id({"chat": {"id": "nested-chat"}}) == "nested-chat"
    assert extract_chat_id({"items": [None, {"chat_id": "list-chat"}]}) == "list-chat"
    assert extract_chat_id({"items": [{"empty": True}]}) is None
    assert extract_chat_id({"chatId": "too-deep"}, depth=6) is None
