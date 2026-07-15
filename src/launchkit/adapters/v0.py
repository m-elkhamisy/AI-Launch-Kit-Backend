"""HTTPX adapter for the v0 generation, hosting, and handoff lifecycle."""

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from launchkit.core.exceptions import ConfigurationError, DomainError, ProviderError
from launchkit.generation.models import (
    ArchiveDownload,
    BuiltPage,
    PipelineStatus,
    V0ChatPrivacy,
    V0GenerationResult,
    V0HandoffResult,
    V0Hook,
)


class V0Adapter:
    """Normalize v0 REST behavior without SDK-specific response objects."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        api_key: str,
        base_url: str = "https://api.v0.dev/v1",
        model_id: str = "v0-max",
    ) -> None:
        if not api_key:
            raise ConfigurationError("v0 API key is required")
        self._client = client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model_id = model_id

    async def create_chat(
        self,
        prompt: str,
        *,
        privacy: V0ChatPrivacy = V0ChatPrivacy.PRIVATE,
    ) -> V0GenerationResult:
        payload = await self._json_request(
            "POST",
            "/chats",
            json={
                "message": prompt,
                "responseMode": "async",
                "chatPrivacy": privacy.value,
                "modelConfiguration": {
                    "modelId": self._model_id,
                    "imageGenerations": True,
                },
            },
        )
        return self._to_result(payload)

    async def host_pages(
        self,
        pages: Sequence[BuiltPage],
        company_name: str,
    ) -> V0GenerationResult:
        if not pages:
            raise DomainError("Cannot host an empty page collection with v0")
        payload = await self._json_request(
            "POST",
            "/chats/init",
            json={
                "type": "files",
                "name": f"{company_name} - site" if company_name else None,
                "chatPrivacy": V0ChatPrivacy.PRIVATE.value,
                "files": [
                    {"name": page.filename, "content": page.html, "locked": True} for page in pages
                ],
            },
        )
        return self._to_result(payload)

    async def get_status(self, chat_id: str) -> V0GenerationResult:
        response = await self._request("GET", f"/chats/{chat_id}")
        if response.status_code == 404:
            return V0GenerationResult(
                chat_id=chat_id,
                web_url=None,
                demo_url=None,
                status=PipelineStatus.PENDING,
                file_count=0,
            )
        return self._to_result(self._parse_response(response))

    async def download_zip(self, chat_id: str) -> ArchiveDownload:
        chat = await self._json_request("GET", f"/chats/{chat_id}")
        version = chat.get("latestVersion")
        version_map = version if isinstance(version, Mapping) else {}
        version_id = version_map.get("id")
        if not isinstance(version_id, str) or not version_id:
            raise DomainError("This chat has no completed version to download yet")
        status = version_map.get("status")
        if status not in {None, PipelineStatus.COMPLETED.value}:
            raise DomainError(f"Build not finished (status: {status})")
        response = await self._request(
            "GET",
            f"/chats/{chat_id}/versions/{version_id}/download",
            params={"format": "zip", "includeDefaultFiles": "true"},
        )
        if response.is_error:
            raise self._response_error(response, "v0 archive download")
        return ArchiveDownload(content=response.content, filename=f"website-{chat_id}.zip")

    async def create_handoff(self, chat_id: str) -> V0HandoffResult:
        chat = await self._json_request("GET", f"/chats/{chat_id}")
        privacy = self._privacy(chat.get("privacy"))
        web_url = chat.get("webUrl")
        if privacy not in {V0ChatPrivacy.UNLISTED, V0ChatPrivacy.PUBLIC}:
            response = await self._request(
                "PATCH",
                f"/chats/{chat_id}",
                json={"chatPrivacy": V0ChatPrivacy.UNLISTED.value},
            )
            if not response.is_error:
                updated = self._parse_response(response)
                privacy = V0ChatPrivacy.UNLISTED
                web_url = updated.get("webUrl", web_url)
        if not isinstance(web_url, str) or not web_url:
            raise ProviderError("v0 did not return a web URL for this chat")
        return V0HandoffResult(chat_id=chat_id, claim_url=web_url, privacy=privacy)

    async def list_hooks(self) -> list[V0Hook]:
        response = await self._request("GET", "/hooks")
        if response.is_error:
            raise self._response_error(response, "v0 hook listing")
        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise ProviderError("v0 returned invalid hook JSON") from exc
        items = payload.get("hooks", []) if isinstance(payload, Mapping) else payload
        return (
            [self._to_hook(item) for item in items if isinstance(item, Mapping)]
            if isinstance(items, list)
            else []
        )

    async def create_hook(self, name: str, url: str, events: Sequence[str]) -> V0Hook:
        payload = await self._json_request(
            "POST", "/hooks", json={"name": name, "url": url, "events": list(events)}
        )
        return self._to_hook(payload)

    async def delete_hook(self, hook_id: str) -> None:
        response = await self._request("DELETE", f"/hooks/{hook_id}")
        if response.is_error and response.status_code != 404:
            raise self._response_error(response, "v0 hook deletion")

    async def _json_request(self, method: str, path: str, **kwargs: Any) -> Mapping[str, Any]:
        return self._parse_response(await self._request(method, path, **kwargs))

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return await self._client.request(
                method,
                f"{self._base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ProviderError(f"v0 network error: {exc}", retryable=True) from exc

    def _parse_response(self, response: httpx.Response) -> Mapping[str, Any]:
        if response.is_error:
            raise self._response_error(response, "v0 request")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("v0 returned a non-JSON response") from exc
        if not isinstance(payload, Mapping):
            raise ProviderError("v0 returned an invalid response object")
        return payload

    @staticmethod
    def _response_error(response: httpx.Response, context: str) -> ProviderError:
        if response.status_code == 402:
            return ProviderError(
                "Out of v0 credits - add credits or enable auto-topup", status_code=402
            )
        return ProviderError(
            f"{context} failed ({response.status_code}): {response.text[:300]}",
            status_code=response.status_code,
            retryable=response.status_code in {429, 500, 502, 503, 504},
        )

    @staticmethod
    def _to_result(chat: Mapping[str, Any]) -> V0GenerationResult:
        chat_id = chat.get("id")
        if not isinstance(chat_id, str) or not chat_id:
            raise ProviderError("v0 returned no chat id")
        version = chat.get("latestVersion")
        version_map = version if isinstance(version, Mapping) else {}
        status_value = version_map.get("status")
        status = (
            PipelineStatus(status_value)
            if status_value in {PipelineStatus.COMPLETED.value, PipelineStatus.FAILED.value}
            else PipelineStatus.PENDING
        )
        web_url = chat.get("webUrl")
        demo_url = version_map.get("demoUrl")
        files = version_map.get("files")
        file_names = (
            [
                str(item.get("name") or item.get("file"))
                for item in files
                if isinstance(item, Mapping) and (item.get("name") or item.get("file"))
            ]
            if isinstance(files, list)
            else []
        )
        version_id = version_map.get("id")
        return V0GenerationResult(
            chat_id=chat_id,
            web_url=web_url if isinstance(web_url, str) else None,
            demo_url=demo_url if isinstance(demo_url, str) else None,
            status=status,
            file_count=len(files) if isinstance(files, list) else 0,
            version_id=version_id if isinstance(version_id, str) else None,
            files=file_names,
        )

    @staticmethod
    def _to_hook(payload: Mapping[str, Any]) -> V0Hook:
        hook_id = payload.get("id")
        url = payload.get("url")
        if not isinstance(hook_id, str) or not isinstance(url, str):
            raise ProviderError("v0 returned an invalid hook")
        events = payload.get("events")
        return V0Hook(
            id=hook_id,
            name=str(payload.get("name") or "AI Launch Kit"),
            url=url,
            events=[str(event) for event in events] if isinstance(events, list) else [],
        )

    @staticmethod
    def _privacy(value: object) -> V0ChatPrivacy | None:
        try:
            return V0ChatPrivacy(value) if isinstance(value, str) else None
        except ValueError:
            return None
