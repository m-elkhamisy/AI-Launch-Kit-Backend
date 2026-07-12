from launchkit.core.config import Settings
from launchkit.main import create_app


def test_application_has_no_business_routes() -> None:
    app = create_app(Settings(environment="test"))
    paths = {getattr(route, "path", None) for route in app.routes}

    assert paths == {"/docs", "/docs/oauth2-redirect", "/openapi.json", "/redoc"}


def test_openapi_metadata_is_available() -> None:
    app = create_app(Settings(environment="test"))
    schema = app.openapi()

    assert schema["info"]["title"] == "AI Launch Kit Backend"
    assert schema["paths"] == {}
