"""Idempotent environment-level v0 hook provisioning tests."""

import asyncio

import pytest

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError
from launchkit.generation.models import V0Hook
from launchkit.hooks import HOOK_NAME, callback_url, provision_v0_hook


class HookGatewayStub:
    def __init__(self, hooks: list[V0Hook]) -> None:
        self.hooks = hooks
        self.created: list[str] = []
        self.deleted: list[str] = []

    async def list_hooks(self) -> list[V0Hook]:
        return self.hooks

    async def create_hook(self, name: str, url: str, events: tuple[str, ...]) -> V0Hook:
        assert name == HOOK_NAME
        self.created.append(url)
        return V0Hook(id="new", name=name, url=url, events=list(events))

    async def delete_hook(self, hook_id: str) -> None:
        self.deleted.append(hook_id)


def hook(identifier: str, url: str, *, name: str = HOOK_NAME) -> V0Hook:
    return V0Hook(
        id=identifier,
        name=name,
        url=url,
        events=["message.finished"],
    )


def test_provision_keeps_one_matching_hook_and_deletes_duplicate() -> None:
    gateway = HookGatewayStub([hook("one", "https://api/hook"), hook("two", "https://api/hook")])

    result = asyncio.run(provision_v0_hook(gateway, "https://api/hook"))

    assert result.id == "one"
    assert gateway.created == []
    assert gateway.deleted == ["two"]


def test_provision_replaces_obsolete_named_hook() -> None:
    gateway = HookGatewayStub(
        [hook("old", "https://old/hook"), hook("other", "https://other", name="Other")]
    )

    result = asyncio.run(provision_v0_hook(gateway, "https://new/hook"))

    assert result.id == "new"
    assert gateway.created == ["https://new/hook"]
    assert gateway.deleted == ["old"]


def test_callback_url_requires_token_and_https_outside_local() -> None:
    with pytest.raises(ConfigurationError, match="TOKEN"):
        callback_url(Settings(environment="production"))
    with pytest.raises(ConfigurationError, match="HTTPS"):
        callback_url(
            Settings(
                environment="production",
                v0_webhook_token="secret",
                v0_webhook_callback_url="http://api.example/hook",
            )
        )

    assert (
        callback_url(
            Settings(
                environment="production",
                v0_webhook_token="secret",
                v0_webhook_callback_url="https://api.example/hook",
            )
        )
        == "https://api.example/hook"
    )
