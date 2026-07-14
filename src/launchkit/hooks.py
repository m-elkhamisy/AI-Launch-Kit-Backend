"""Provision the single environment-level v0 completion hook."""

import argparse
import asyncio
from typing import Protocol
from urllib.parse import urlparse

import httpx

from launchkit.adapters.v0 import V0Adapter
from launchkit.core.config import Settings, get_settings
from launchkit.core.exceptions import ConfigurationError
from launchkit.generation.models import V0Hook

HOOK_NAME = "AI Launch Kit message completion"
HOOK_EVENTS = ("message.finished",)


class HookGateway(Protocol):
    async def list_hooks(self) -> list[V0Hook]:
        """List environment hooks."""

    async def create_hook(self, name: str, url: str, events: tuple[str, ...]) -> V0Hook:
        """Create one environment hook."""

    async def delete_hook(self, hook_id: str) -> None:
        """Delete one obsolete hook."""


async def provision_v0_hook(gateway: HookGateway, callback_url: str) -> V0Hook:
    hooks = await gateway.list_hooks()
    matches = [
        hook
        for hook in hooks
        if hook.url == callback_url and set(HOOK_EVENTS).issubset(hook.events)
    ]
    if matches:
        for duplicate in matches[1:]:
            await gateway.delete_hook(duplicate.id)
        return matches[0]
    created = await gateway.create_hook(HOOK_NAME, callback_url, HOOK_EVENTS)
    for obsolete in hooks:
        if obsolete.name == HOOK_NAME and obsolete.id != created.id:
            await gateway.delete_hook(obsolete.id)
    return created


def callback_url(settings: Settings) -> str:
    token = settings.v0_webhook_token.get_secret_value() if settings.v0_webhook_token else ""
    if not token:
        raise ConfigurationError("LAUNCHKIT_V0_WEBHOOK_TOKEN is required")
    value = settings.v0_webhook_callback_url or (
        f"{settings.site_url.rstrip('/')}/api/v1/webhooks/v0/{token}"
    )
    parsed = urlparse(value)
    if parsed.scheme != "https" and settings.environment not in {"local", "test"}:
        raise ConfigurationError("The v0 webhook callback must use HTTPS")
    return value


async def _provision() -> None:
    settings = get_settings()
    api_key = settings.v0_api_key.get_secret_value() if settings.v0_api_key else ""
    if not api_key:
        raise ConfigurationError("LAUNCHKIT_V0_API_KEY is required")
    async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10)) as client:
        adapter = V0Adapter(
            client,
            api_key=api_key,
            base_url=settings.v0_base_url,
            model_id=settings.v0_model,
        )
        await provision_v0_hook(adapter, callback_url(settings))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage AI Launch Kit provider hooks")
    parser.add_argument("action", choices=["provision-v0"])
    parser.parse_args()
    asyncio.run(_provision())


if __name__ == "__main__":
    main()
