"""IC OAuth login bridging into the persisted V1 API."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from launchkit.auth.cookies import dump_signed
from launchkit.auth.pkce import generate_code_verifier
from launchkit.core.config import Settings
from launchkit.main import create_app
from launchkit.persistence import Database, create_database
from launchkit.persistence.base import Base
from launchkit.persistence.models import UserRecord


@contextmanager
def ic_client(tmp_path: Path) -> Iterator[tuple[TestClient, Database, Settings]]:
    settings = Settings(
        environment="test",
        auth_mode="fixed_otp",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'ic.sqlite3').as_posix()}",
        auth_base_url="https://auth.example.com",
        auth_client_id="launchkit-dev",
        auth_redirect_uri="http://localhost:8000/auth/callback",
        auth_frontend_url="http://localhost:5173",
        auth_session_secret="test-secret",
    )
    database = create_database(settings)

    async def create_schema() -> None:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    with TestClient(create_app(settings, database)) as client:
        yield client, database, settings


def _login_via_callback(client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    verifier = generate_code_verifier()
    state = dump_signed({"code_verifier": verifier}, settings.auth_session_secret)

    async def fake_exchange(self: object, *, code: str, code_verifier: str) -> dict[str, object]:
        return {"access_token": "access-1", "refresh_token": "refresh-1", "expires_in": 3600}

    async def fake_me(self: object, *, access_token: str) -> dict[str, object]:
        return {
            "cognitoUserId": "sub-ic-1",
            "email": "user@example.com",
            "fullName": "Jane Doe",
            "role": "customer",
            "pool": "inc-customer-pool",
        }

    monkeypatch.setattr("launchkit.auth.client.AuthServiceClient.exchange_code", fake_exchange)
    monkeypatch.setattr("launchkit.auth.client.AuthServiceClient.me", fake_me)

    response = client.get(f"/auth/callback?code=auth-code&state={state}", follow_redirects=False)
    assert response.status_code == 302
    assert "auth=success" in response.headers["location"]


def test_ic_login_persists_user_and_grants_api_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with ic_client(tmp_path) as (client, database, settings):
        # Unauthenticated /api/v1 access is rejected in fixed_otp mode.
        assert client.get("/api/v1/projects").status_code == 401

        _login_via_callback(client, settings, monkeypatch)

        # The IC login was recorded in the users table.
        async def fetch_user() -> UserRecord | None:
            async with database.session() as session:
                return (await session.scalars(select(UserRecord))).one_or_none()

        user = asyncio.run(fetch_user())
        assert user is not None
        assert user.id == "sub-ic-1"
        assert user.email == "user@example.com"
        assert user.full_name == "Jane Doe"

        # The lk_api_token cookie authenticates /api/v1 requests as this user.
        assert client.get("/api/v1/projects").status_code == 200
        created = client.post("/api/v1/projects", json={})
        assert created.status_code == 201

        # /auth/token returns a bearer token the SPA can store.
        token_response = client.get("/auth/token")
        assert token_response.status_code == 200
        token = token_response.json()["accessToken"]
        client.cookies.delete("lk_api_token")
        bearer = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {token}"})
        assert bearer.status_code == 200
