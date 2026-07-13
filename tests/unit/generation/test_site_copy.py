"""Best-effort site-copy extraction tests."""

import asyncio
from collections.abc import Mapping
from typing import Any

from launchkit.generation.site_copy import SiteCopyExtractor


class JsonStub:
    def __init__(self, payload: Mapping[str, Any] | Exception) -> None:
        self.payload = payload
        self.prompt = ""

    async def generate_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 2_000,
        model: str | None = None,
    ) -> Mapping[str, Any]:
        del system, max_tokens, model
        self.prompt = prompt
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_site_copy_extractor_validates_existing_copy_and_truncates_html() -> None:
    stub = JsonStub(
        {
            "headline": "Hello",
            "subheadline": "World",
            "sections": [],
            "callToAction": "Contact",
        }
    )
    result = asyncio.run(SiteCopyExtractor(stub).extract("x" * 13_000))
    assert result is not None and result.headline == "Hello"
    assert len(stub.prompt) < 12_500


def test_site_copy_extractor_is_best_effort() -> None:
    assert asyncio.run(SiteCopyExtractor(JsonStub(RuntimeError("down"))).extract("html")) is None
    assert asyncio.run(SiteCopyExtractor(JsonStub({"invalid": True})).extract("html")) is None
