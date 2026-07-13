"""Mock HTTP tests for Vercel deployment and transfer behavior."""

import asyncio
import json

import httpx
import pytest

from launchkit.adapters.vercel import VercelAdapter, project_name
from launchkit.core.exceptions import ConfigurationError, ProviderError
from launchkit.deployment.models import DeploymentFile


def test_project_name_normalizes_and_caps_chat_identifier() -> None:
    assert project_name("Chat ID!") == "ic-site-chat-id"
    assert len(project_name("a" * 200)) == 90
    assert project_name("!!!") == "ic-site"


def test_vercel_requires_token() -> None:
    with pytest.raises(ConfigurationError):
        VercelAdapter(httpx.AsyncClient(), token="")


def test_create_deployment_and_transfer_code_send_expected_contract() -> None:
    requests: list[httpx.Request] = []
    replies = iter(
        [
            httpx.Response(
                201, json={"projectId": "project-1", "id": "dep-1", "url": "x.vercel.app"}
            ),
            httpx.Response(200, json={"code": "claim-code"}),
        ]
    )

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return next(replies)

    adapter = VercelAdapter(
        httpx.AsyncClient(transport=httpx.MockTransport(handle)), token="token", team_id="team"
    )

    async def scenario() -> tuple[str, str]:
        deployment = await adapter.create_deployment(
            "chat-1", [DeploymentFile(file="index.html", data="<html />")]
        )
        code = await adapter.create_transfer_code(deployment.project_id)
        return deployment.project_id, code

    assert asyncio.run(scenario()) == ("project-1", "claim-code")
    body = json.loads(requests[0].content)
    assert body["target"] == "production"
    assert body["files"] == [{"file": "index.html", "data": "<html />"}]
    assert requests[0].url.params["teamId"] == "team"


def test_vercel_falls_back_to_project_name_and_optional_fields() -> None:
    adapter = VercelAdapter(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: httpx.Response(202, json={}))
        ),
        token="token",
    )
    result = asyncio.run(adapter.create_deployment("Chat ID", []))
    assert result.project_id == "ic-site-chat-id"
    assert result.deployment_id is None
    assert result.url is None


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="down"),
        httpx.Response(200, text="bad"),
        httpx.Response(200, json=[]),
    ],
)
def test_vercel_normalizes_invalid_responses(response: httpx.Response) -> None:
    adapter = VercelAdapter(
        httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: response)), token="token"
    )
    with pytest.raises(ProviderError):
        asyncio.run(adapter.create_transfer_code("project"))


def test_vercel_requires_transfer_code() -> None:
    adapter = VercelAdapter(
        httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={}))
        ),
        token="token",
    )
    with pytest.raises(ProviderError, match="transfer code"):
        asyncio.run(adapter.create_transfer_code("project"))
