"""Provider-neutral generation boundaries used by application capabilities."""

from collections.abc import Mapping
from typing import Any, Protocol


class TextGenerator(Protocol):
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate plain text without exposing provider response objects."""


class StructuredGenerator(Protocol):
    async def generate_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 2_000,
        model: str | None = None,
    ) -> Mapping[str, Any]:
        """Generate and parse one JSON object."""


class ImageGenerator(Protocol):
    async def generate_image(self, prompt: str) -> str:
        """Generate one image and return a provider-neutral data URL."""


class ImageSearch(Protocol):
    async def search_image(self, query: str) -> tuple[str, str | None] | None:
        """Return an image URL and optional credit for a search query."""
