"""Mock HTTP tests for v0 generation, status, archive, and handoff."""

import asyncio
import json

import httpx
import pytest

from launchkit.adapters.v0 import V0Adapter
from launchkit.core.exceptions import ConfigurationError, DomainError, ProviderError
from launchkit.generation.models import BuiltPage, PipelineStatus, V0ChatPrivacy


def chat_response(
    *, status: str = "completed", privacy: str = "private", web_url: str | None = "https://v0/chat"
) -> dict[str, object]:
    return {
        "id": "chat-1",
        "webUrl": web_url,
        "privacy": privacy,
        "latestVersion": {
            "id": "version-1",
            "status": status,
            "demoUrl": "https://demo",
            "files": [{"name": "index.html"}],
        },
    }


def test_v0_requires_key() -> None:
    with pytest.raises(ConfigurationError):
        V0Adapter(httpx.AsyncClient(), api_key="")


def test_create_chat_uses_async_private_generation_and_normalizes_result() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=chat_response(status="building"))

    adapter = V0Adapter(httpx.AsyncClient(transport=httpx.MockTransport(handle)), api_key="key")
    result = asyncio.run(adapter.create_chat("Build it"))
    body = json.loads(requests[0].content)

    assert result.status is PipelineStatus.PENDING
    assert result.file_count == 1
    assert body["responseMode"] == "async"
    assert body["chatPrivacy"] == "private"
    assert body["modelConfiguration"]["modelId"] == "v0-max"


def test_host_pages_locks_exact_files_and_rejects_empty_input() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=chat_response())

    adapter = V0Adapter(httpx.AsyncClient(transport=httpx.MockTransport(handle)), api_key="key")
    page = BuiltPage(name="Home", slug="index", filename="index.html", html="<html />")
    result = asyncio.run(adapter.host_pages([page], "Acme"))

    assert result.status is PipelineStatus.COMPLETED
    assert json.loads(requests[0].content)["files"] == [
        {"name": "index.html", "content": "<html />", "locked": True}
    ]
    with pytest.raises(DomainError):
        asyncio.run(adapter.host_pages([], "Acme"))


def test_get_status_treats_404_as_pending() -> None:
    adapter = V0Adapter(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: httpx.Response(404, text="missing"))
        ),
        api_key="key",
    )
    result = asyncio.run(adapter.get_status("new-chat"))

    assert result.chat_id == "new-chat"
    assert result.status is PipelineStatus.PENDING
    assert result.web_url is None


def test_download_zip_resolves_version_and_returns_archive() -> None:
    responses = iter(
        [httpx.Response(200, json=chat_response()), httpx.Response(200, content=b"zip")]
    )
    adapter = V0Adapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: next(responses))),
        api_key="key",
    )

    result = asyncio.run(adapter.download_zip("chat-1"))

    assert result.content == b"zip"
    assert result.filename == "website-chat-1.zip"


@pytest.mark.parametrize(
    "chat",
    [
        {"id": "chat-1", "latestVersion": {}},
        chat_response(status="building"),
    ],
)
def test_download_zip_requires_completed_version(chat: dict[str, object]) -> None:
    adapter = V0Adapter(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json=chat))
        ),
        api_key="key",
    )

    with pytest.raises(DomainError):
        asyncio.run(adapter.download_zip("chat-1"))


def test_handoff_makes_private_chat_unlisted() -> None:
    responses = iter(
        [
            httpx.Response(200, json=chat_response()),
            httpx.Response(200, json={"webUrl": "https://v0/unlisted"}),
        ]
    )
    adapter = V0Adapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: next(responses))),
        api_key="key",
    )

    result = asyncio.run(adapter.create_handoff("chat-1"))

    assert result.privacy is V0ChatPrivacy.UNLISTED
    assert result.claim_url == "https://v0/unlisted"


def test_handoff_keeps_public_url_and_tolerates_failed_privacy_update() -> None:
    public = V0Adapter(
        httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(200, json=chat_response(privacy="public"))
            )
        ),
        api_key="key",
    )
    assert asyncio.run(public.create_handoff("chat-1")).privacy is V0ChatPrivacy.PUBLIC

    responses = iter([httpx.Response(200, json=chat_response()), httpx.Response(500)])
    private = V0Adapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: next(responses))),
        api_key="key",
    )
    assert asyncio.run(private.create_handoff("chat-1")).claim_url == "https://v0/chat"


@pytest.mark.parametrize(
    "response",
    [httpx.Response(402, text="credits"), httpx.Response(500, text="down")],
)
def test_v0_errors_are_normalized(response: httpx.Response) -> None:
    adapter = V0Adapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: response)), api_key="key"
    )
    with pytest.raises(ProviderError):
        asyncio.run(adapter.create_chat("prompt"))
