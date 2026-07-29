from launchkit.core.config import Settings
from launchkit.main import create_app


def test_application_registers_auth_routes() -> None:
    app = create_app(Settings(environment="test"))
    paths = set(app.openapi()["paths"])

    assert "/auth/login" in paths
    assert "/auth/callback" in paths
    assert "/auth/me" in paths
    assert "/auth/refresh" in paths
    assert "/auth/logout" in paths


def test_openapi_metadata_is_available() -> None:
    app = create_app(Settings(environment="test"))
    schema = app.openapi()

    assert schema["info"]["title"] == "AI Launch Kit Backend"
    assert "/auth/login" in schema["paths"]
    assert "/auth/me" in schema["paths"]
