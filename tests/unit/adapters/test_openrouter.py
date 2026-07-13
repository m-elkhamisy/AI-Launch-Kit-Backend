"""Mock-transport tests for the OpenRouter adapter."""

import asyncio
import json

import httpx
import pytest

from launchkit.adapters.llm_queue import RequestQueue
from launchkit.adapters.openrouter import OpenRouterAdapter, strip_code_fence
from launchkit.core.exceptions import ConfigurationError, ProviderError


def adapter_for(
    handler: httpx.MockTransport,
    *,
    attempts: int = 1,
    sleeps: list[float] | None = None,
) -> OpenRouterAdapter:
    async def sleep(delay: float) -> None:
        if sleeps is not None:
            sleeps.append(delay)

    return OpenRouterAdapter(
        httpx.AsyncClient(transport=handler),
        RequestQueue(min_gap_seconds=0),
        api_key="secret",
        max_attempts=attempts,
        sleep=sleep,
        jitter=lambda: 0.0,
    )


def response(message: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": message}]})


def test_adapter_requires_key_and_strips_supported_fences() -> None:
    with pytest.raises(ConfigurationError):
        OpenRouterAdapter(httpx.AsyncClient(), RequestQueue(), api_key="")
    assert strip_code_fence("```tsx\n<div />\n```") == "<div />"


def test_generate_text_sends_normalized_request() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response({"content": "hello"})

    adapter = adapter_for(httpx.MockTransport(handle))
    result = asyncio.run(
        adapter.generate_text("prompt", system="rules", max_tokens=50, temperature=0.2)
    )
    body = json.loads(requests[0].content)

    assert result == "hello"
    assert requests[0].headers["authorization"] == "Bearer secret"
    assert body["messages"][0] == {"role": "system", "content": "rules"}
    assert body["temperature"] == 0.2


def test_generate_json_image_label_and_profile_fields() -> None:
    replies = iter(
        [
            response({"content": '```json\n{"value": 2}\n```'}),
            response({"images": [{"image_url": {"url": "data:image/png;base64,abc"}}]}),
            response({"content": "logo"}),
            response(
                {
                    "content": '{"fields":{"companyName":"Acme"},'
                    '"designHints":{"tagline":"Clear","cta":"Call"}}'
                }
            ),
        ]
    )
    adapter = adapter_for(httpx.MockTransport(lambda _request: next(replies)))

    async def scenario() -> tuple[object, str, str, str | None]:
        payload = await adapter.generate_json("json")
        image = await adapter.generate_image("image")
        label = await adapter.label_image("data:image/png;base64,abc")
        fields = await adapter.extract_profile_fields("profile")
        return payload, image, label, fields.fields.company_name

    assert asyncio.run(scenario()) == (
        {"value": 2},
        "data:image/png;base64,abc",
        "logo",
        "Acme",
    )


def test_adapter_retries_429_using_retry_after_and_shared_queue() -> None:
    calls = 0
    sleeps: list[float] = []

    def handle(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"error": {"message": "limited", "code": 429}},
            )
        return response({"content": "ok"})

    adapter = adapter_for(httpx.MockTransport(handle), attempts=2, sleeps=sleeps)

    assert asyncio.run(adapter.generate_text("prompt")) == "ok"
    assert calls == 2
    assert sleeps == [2.0]


@pytest.mark.parametrize(
    "provider_response",
    [
        httpx.Response(401, json={"error": {"message": "bad key", "code": 401}}),
        httpx.Response(200, json={"error": {"message": "bad model", "code": 400}}),
        httpx.Response(200, text="not-json"),
    ],
)
def test_adapter_normalizes_terminal_provider_errors(provider_response: httpx.Response) -> None:
    adapter = adapter_for(httpx.MockTransport(lambda _request: provider_response))

    with pytest.raises(ProviderError):
        asyncio.run(adapter.generate_text("prompt"))


@pytest.mark.parametrize(
    "content",
    ["", "[]", "not-json"],
)
def test_generate_json_rejects_empty_non_object_or_invalid_content(content: str) -> None:
    adapter = adapter_for(httpx.MockTransport(lambda _request: response({"content": content})))

    with pytest.raises(ProviderError):
        asyncio.run(adapter.generate_json("prompt"))


def test_image_and_profile_validation_errors_are_normalized() -> None:
    replies = iter(
        [
            response({"images": []}),
            response({"images": [{}]}),
            response({"content": '{"fields":{"unknown":true},"designHints":{}}'}),
        ]
    )
    adapter = adapter_for(httpx.MockTransport(lambda _request: next(replies)))

    with pytest.raises(ProviderError):
        asyncio.run(adapter.generate_image("prompt"))
    with pytest.raises(ProviderError):
        asyncio.run(adapter.generate_image("prompt"))
    with pytest.raises(ProviderError):
        asyncio.run(adapter.extract_profile_fields("profile"))
