from launchkit.core.config import Settings
from launchkit.main import create_app


def test_application_registers_v1_routes() -> None:
    app = create_app(Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:"))
    paths = set(app.openapi()["paths"])

    assert {
        "/api/v1/catalogs/wizard",
        "/api/v1/health",
        "/api/v1/projects",
        "/api/v1/projects/{project_id}",
    } <= paths


def test_openapi_metadata_and_contract_are_available() -> None:
    app = create_app(Settings(environment="test", database_url="sqlite+aiosqlite:///:memory:"))
    schema = app.openapi()

    assert schema["info"]["title"] == "AI Launch Kit Backend"
    assert schema["info"]["version"] == "1.0.0"
    assert schema["paths"]["/api/v1/projects"]["post"]["responses"]["201"]
    assert schema["paths"]["/api/v1/projects"]["get"]["responses"]["200"]
