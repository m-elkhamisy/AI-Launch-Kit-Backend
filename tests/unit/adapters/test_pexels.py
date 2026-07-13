"""Mock HTTP tests for the graceful Pexels adapter."""

import asyncio

import httpx
import pytest

from launchkit.adapters.pexels import PexelsAdapter


def test_pexels_returns_first_large_landscape_photo() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "photos": [
                    {
                        "src": {"large2x": "https://image/large", "large": "https://image"},
                        "photographer": "Ada",
                    }
                ]
            },
        )

    adapter = PexelsAdapter(httpx.AsyncClient(transport=httpx.MockTransport(handle)), api_key="key")

    assert asyncio.run(adapter.search_image("bakery")) == ("https://image/large", "Ada")
    assert requests[0].url.params["orientation"] == "landscape"
    assert requests[0].headers["authorization"] == "key"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"photos": [{}]}),
        httpx.Response(200, json={"photos": [{"src": {}}]}),
        httpx.Response(200, text="invalid"),
    ],
)
def test_pexels_degrades_to_no_result(response: httpx.Response) -> None:
    adapter = PexelsAdapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: response)), api_key="key"
    )

    assert asyncio.run(adapter.search_image("query")) is None


def test_pexels_without_key_does_not_call_network() -> None:
    adapter = PexelsAdapter(httpx.AsyncClient(), api_key=None)
    assert asyncio.run(adapter.search_image("query")) is None
