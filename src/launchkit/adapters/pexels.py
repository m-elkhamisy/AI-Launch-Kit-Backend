"""Pexels image-search adapter with graceful no-result behavior."""

from collections.abc import Mapping
from typing import Any

import httpx


class PexelsAdapter:
    """Return the first landscape image without leaking Pexels response types."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str | None,
        base_url: str = "https://api.pexels.com/v1",
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def search_image(self, query: str) -> tuple[str, str | None] | None:
        if not self._api_key:
            return None
        try:
            response = await self._client.get(
                f"{self._base_url}/search",
                params={"query": query, "per_page": 1, "orientation": "landscape"},
                headers={"Authorization": self._api_key},
            )
            if response.is_error:
                return None
            payload: Any = response.json()
        except (httpx.RequestError, ValueError):
            return None
        if not isinstance(payload, Mapping):
            return None
        photos = payload.get("photos")
        photo = photos[0] if isinstance(photos, list) and photos else None
        if not isinstance(photo, Mapping):
            return None
        sources = photo.get("src")
        if not isinstance(sources, Mapping):
            return None
        source = sources.get("large2x") or sources.get("large")
        if not isinstance(source, str) or not source:
            return None
        photographer = photo.get("photographer")
        return source, photographer if isinstance(photographer, str) else None
