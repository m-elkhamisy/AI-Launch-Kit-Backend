from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from launchkit.auth.cookies import dump_signed
from launchkit.auth.pkce import code_challenge_s256, generate_code_verifier
from launchkit.core.config import Settings
from launchkit.core.exceptions import ProviderError
from launchkit.main import create_app


def _settings(**overrides: object) -> Settings:
    base = {
        "environment": "test",
        "auth_base_url": "https://auth.example.com",
        "auth_client_id": "launchkit-dev",
        "auth_redirect_uri": "http://localhost:8000/auth/callback",
        "auth_frontend_url": "http://localhost:5173",
        "auth_session_secret": "test-secret",
        "auth_cors_origins": "http://localhost:5173",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_login_redirects_to_ic_authorize() -> None:
    client = TestClient(create_app(_settings()))
    response = client.get("/auth/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://auth.example.com/aws/v1/auth/authorize?")
    query = parse_qs(urlparse(location).query)
    assert query["client_id"] == ["launchkit-dev"]
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]
    assert "code_challenge" in query
    assert "state" in query
    assert "lk_oauth_pending" in response.cookies


def test_login_without_client_id_returns_503() -> None:
    client = TestClient(create_app(_settings(auth_client_id=None)))
    response = client.get("/auth/login", follow_redirects=False)
    assert response.status_code == 503


def test_callback_exchanges_code_and_sets_cookies(monkeypatch: object) -> None:
    settings = _settings()
    app = create_app(settings)
    verifier = generate_code_verifier()
    state = "state-abc"
    pending = dump_signed(
        {"state": state, "code_verifier": verifier},
        settings.auth_session_secret,
    )

    async def fake_exchange(
        self: object,
        *,
        code: str,
        code_verifier: str,
    ) -> dict[str, str | int]:
        assert code == "auth-code"
        assert code_verifier == verifier
        return {
            "access_token": "access-1",
            "refresh_token": "refresh-1",
            "expires_in": 3600,
            "token_type": "Bearer",
        }

    monkeypatch.setattr(
        "launchkit.auth.client.AuthServiceClient.exchange_code",
        fake_exchange,
    )

    client = TestClient(app)
    client.cookies.set("lk_oauth_pending", pending)
    response = client.get(
        f"/auth/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith("http://localhost:5173/?")
    assert "auth=success" in response.headers["location"]
    assert response.cookies.get("lk_access_token") == "access-1"
    assert response.cookies.get("lk_refresh_token") == "refresh-1"


def test_callback_rejects_state_mismatch() -> None:
    settings = _settings()
    pending = dump_signed(
        {"state": "expected", "code_verifier": "verifier"},
        settings.auth_session_secret,
    )
    client = TestClient(create_app(settings))
    client.cookies.set("lk_oauth_pending", pending)
    response = client.get(
        "/auth/callback?code=auth-code&state=wrong",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "reason=state_mismatch" in response.headers["location"]


def test_me_unauthenticated() -> None:
    client = TestClient(create_app(_settings()))
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False, "user": None}


def test_me_authenticated(monkeypatch: object) -> None:
    async def fake_me(self: object, *, access_token: str) -> dict[str, object]:
        assert access_token == "access-1"
        return {
            "cognitoUserId": "sub-1",
            "email": "user@example.com",
            "fullName": "Jane Doe",
            "role": "customer",
            "pool": "inc-customer-pool",
        }

    monkeypatch.setattr("launchkit.auth.client.AuthServiceClient.me", fake_me)
    client = TestClient(create_app(_settings()))
    client.cookies.set("lk_access_token", "access-1")
    response = client.get("/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == "user@example.com"
    assert body["user"]["cognitoUserId"] == "sub-1"


def test_me_refreshes_expired_access_token(monkeypatch: object) -> None:
    calls = {"me": 0}

    async def fake_me(self: object, *, access_token: str) -> dict[str, object]:
        calls["me"] += 1
        if access_token == "expired":
            raise ProviderError("unauthorized", status_code=401, provider_name="app-auth")
        return {"cognitoUserId": "sub-1", "email": "user@example.com", "role": "customer"}

    async def fake_refresh(self: object, *, refresh_token: str) -> dict[str, object]:
        assert refresh_token == "refresh-1"
        return {"accessToken": "fresh-access", "expiresIn": 3600, "tokenType": "Bearer"}

    monkeypatch.setattr("launchkit.auth.client.AuthServiceClient.me", fake_me)
    monkeypatch.setattr("launchkit.auth.client.AuthServiceClient.refresh", fake_refresh)

    client = TestClient(create_app(_settings()))
    client.cookies.set("lk_access_token", "expired")
    client.cookies.set("lk_refresh_token", "refresh-1")
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True
    assert response.cookies.get("lk_access_token") == "fresh-access"
    assert calls["me"] == 2


def test_pkce_challenge_is_s256() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert code_challenge_s256(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
