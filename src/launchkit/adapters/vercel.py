"""HTTPX adapter for Vercel production deployments and transfer requests."""

from collections.abc import Mapping, Sequence
from typing import Any

import httpx

from launchkit.core.exceptions import ConfigurationError, ProviderError
from launchkit.deployment.models import DeploymentFile, VercelDeployment


def project_name(chat_id: str) -> str:
    slug = "".join(character if character.isalnum() else "-" for character in chat_id.lower())
    cleaned = slug.strip("-")
    return f"ic-site-{cleaned}"[:90] if cleaned else "ic-site"


class VercelAdapter:
    """Normalize Vercel deployment and transfer responses."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        token: str,
        team_id: str | None = None,
        base_url: str = "https://api.vercel.com",
    ) -> None:
        if not token:
            raise ConfigurationError("Vercel token is required")
        self._client = client
        self._token = token
        self._team_id = team_id
        self._base_url = base_url.rstrip("/")

    async def create_deployment(
        self, chat_id: str, files: Sequence[DeploymentFile]
    ) -> VercelDeployment:
        payload = await self._request(
            "POST",
            "/v13/deployments",
            params=self._params(skipAutoDetectionConfirmation="1"),
            json={
                "name": project_name(chat_id),
                "files": [file.model_dump(exclude_none=True) for file in files],
                "target": "production",
                "projectSettings": {"framework": "nextjs"},
            },
        )
        project = payload.get("projectId") or project_name(chat_id)
        if not isinstance(project, str):
            raise ProviderError("Vercel returned an invalid project identifier")
        deployment_id = payload.get("id")
        url = payload.get("url")
        return VercelDeployment(
            project_id=project,
            deployment_id=deployment_id if isinstance(deployment_id, str) else None,
            url=url if isinstance(url, str) else None,
        )

    async def create_transfer_code(self, project_id_or_name: str) -> str:
        payload = await self._request(
            "POST",
            f"/v9/projects/{project_id_or_name}/transfer-request",
            params=self._params(),
            json={},
        )
        code = payload.get("code")
        if not isinstance(code, str) or not code:
            raise ProviderError("Vercel returned no transfer code")
        return code

    def _params(self, **values: str) -> dict[str, str]:
        params = dict(values)
        if self._team_id:
            params["teamId"] = self._team_id
        return params

    async def _request(self, method: str, path: str, **kwargs: Any) -> Mapping[str, Any]:
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                **kwargs,
            )
        except httpx.RequestError as exc:
            raise ProviderError(f"Vercel network error: {exc}", retryable=True) from exc
        if response.status_code not in {200, 201, 202}:
            raise ProviderError(
                f"Vercel request failed ({response.status_code}): {response.text[:300]}",
                status_code=response.status_code,
                retryable=response.status_code in {429, 500, 502, 503, 504},
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderError("Vercel returned a non-JSON response") from exc
        if not isinstance(payload, Mapping):
            raise ProviderError("Vercel returned an invalid response object")
        return payload
