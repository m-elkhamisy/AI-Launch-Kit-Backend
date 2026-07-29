"""HTTP client for InnovationCity app-auth OAuth endpoints."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, ProviderError


class AuthServiceClient:
    """Thin wrapper around IC ``/aws/v1/auth/*`` OAuth + session APIs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base = settings.auth_base_url.rstrip("/")

    def _require_oauth_config(self) -> tuple[str, str]:
        client_id = self._settings.auth_client_id
        redirect_uri = self._settings.auth_redirect_uri
        if not client_id or not redirect_uri:
            raise ConfigurationError(
                "OAuth is not configured. Set LAUNCHKIT_AUTH_CLIENT_ID and "
                "LAUNCHKIT_AUTH_REDIRECT_URI (register both with WeCan)."
            )
        return client_id, redirect_uri

    def build_authorize_url(self, *, code_challenge: str, state: str) -> str:
        client_id, redirect_uri = self._require_oauth_config()
        query = urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )
        return f"{self._base}/aws/v1/auth/authorize?{query}"

    def build_logout_url(self, *, state: str | None = None) -> str:
        client_id = self._settings.auth_client_id
        post_logout = self._settings.auth_post_logout_redirect_uri
        if not client_id or not post_logout:
            raise ConfigurationError(
                "Logout is not configured. Set LAUNCHKIT_AUTH_CLIENT_ID and "
                "LAUNCHKIT_AUTH_POST_LOGOUT_REDIRECT_URI."
            )
        params: dict[str, str] = {
            "client_id": client_id,
            "post_logout_redirect_uri": post_logout,
        }
        if state:
            params["state"] = state
        return f"{self._base}/aws/v1/auth/oauth/logout?{urlencode(params)}"

    async def exchange_code(self, *, code: str, code_verifier: str) -> dict[str, Any]:
        client_id, redirect_uri = self._require_oauth_config()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
        return await self._post_json("/aws/v1/auth/oauth/token", payload)

    async def refresh(self, *, refresh_token: str) -> dict[str, Any]:
        return await self._post_json(
            "/aws/v1/auth/refresh",
            {"refreshToken": refresh_token},
        )

    async def me(self, *, access_token: str) -> dict[str, Any]:
        return await self._get_json("/aws/v1/auth/me", access_token=access_token)

    async def revoke_session(self, *, access_token: str, refresh_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                f"{self._base}/aws/v1/auth/session",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"refreshToken": refresh_token},
            )
        return self._parse(response, provider="app-auth-session")

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base}{path}",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        return self._parse(response, provider=f"app-auth{path}")

    async def _get_json(self, path: str, *, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._base}{path}",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        return self._parse(response, provider=f"app-auth{path}")

    @staticmethod
    def _parse(response: httpx.Response, *, provider: str) -> dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            data = {"error": response.text or "invalid response"}
        if response.is_success:
            if not isinstance(data, dict):
                raise ProviderError(
                    "Unexpected auth service response shape",
                    status_code=response.status_code,
                    provider_name=provider,
                )
            return data
        message = "Auth service request failed"
        if isinstance(data, dict):
            err = data.get("error") or data.get("message")
            if isinstance(err, str) and err:
                message = err
        raise ProviderError(
            message,
            status_code=response.status_code,
            provider_name=provider,
            retryable=response.status_code >= 500,
        )
