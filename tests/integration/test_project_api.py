"""V1 project and wizard transport integration tests."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from launchkit.core.config import Settings
from launchkit.main import create_app
from launchkit.persistence import create_database
from launchkit.persistence.base import Base


@contextmanager
def api_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'api.sqlite3').as_posix()}",
        frontend_origins="http://localhost:5173,https://studio.example",
    )
    database = create_database(settings)

    async def create_schema() -> None:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    with TestClient(create_app(settings, database)) as client:
        yield client


def create_project(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/v1/projects", json={})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def test_health_catalog_and_cors_contract(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        health = client.get("/api/v1/health")
        catalog = client.get("/api/v1/catalogs/wizard")
        preflight = client.options(
            "/api/v1/projects",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert health.json() == {"status": "ok", "environment": "test", "version": "1.0.0"}
    assert health.headers["x-request-id"].startswith("req_")
    body = catalog.json()
    assert body["businessCategories"][7]["id"] == "tech-saas"
    assert body["palettes"][0]["colors"]["primary"].startswith("#")
    assert body["pageTemplates"][0]["sectionTemplateIds"][0] == "navigation"
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_project_create_get_and_partial_patch(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        project = create_project(client)
        project_id = project["id"]

        updated = client.patch(
            f"/api/v1/projects/{project_id}",
            json={
                "business": {
                    "companyName": "Northstar",
                    "categoryId": "creative-agency",
                    "targetAudience": "Founders",
                },
                "design": {
                    "moodId": "editorial",
                    "animationId": "low",
                    "tagline": "Ideas made visible",
                },
            },
        )
        fetched = client.get(f"/api/v1/projects/{project_id}")

    assert updated.status_code == 200
    assert updated.json()["business"]["companyName"] == "Northstar"
    assert updated.json()["business"]["uvp"] == ""
    assert updated.json()["design"]["paletteId"] == "modern-blue"
    assert fetched.json() == updated.json()
    assert len(fetched.json()["pageLayout"]["pages"]) == 3


def test_missing_project_uses_safe_error_envelope(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        response = client.get("/api/v1/projects/prj_missing")

    assert response.status_code == 404
    assert response.json()["error"] == {
        "code": "project_not_found",
        "message": "Project not found.",
        "details": [],
        "requestId": response.headers["x-request-id"],
    }


def invalid_layouts(project: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    layout = project["pageLayout"]
    cases: list[tuple[str, dict[str, Any]]] = []

    empty = deepcopy(layout)
    empty["pages"] = []
    cases.append(("one or more pages", empty))

    too_many_pages = deepcopy(layout)
    page = too_many_pages["pages"][0]
    too_many_pages["pages"] = []
    for index in range(7):
        copy = deepcopy(page)
        copy["id"] = f"page:{index}"
        copy["templateId"] = "home" if index == 0 else "about"
        copy["slug"] = f"page-{index}"
        too_many_pages["pages"].append(copy)
    cases.append(("at most 6 pages", too_many_pages))

    duplicate_slug = deepcopy(layout)
    duplicate_slug["pages"][1]["slug"] = duplicate_slug["pages"][0]["slug"]
    cases.append(("unique slugs", duplicate_slug))

    missing_navigation = deepcopy(layout)
    missing_navigation["pages"][0]["sections"] = missing_navigation["pages"][0]["sections"][1:]
    cases.append(("locked navigation", missing_navigation))

    unknown_section = deepcopy(layout)
    unknown_section["pages"][0]["sections"][1]["templateId"] = "made-up"
    cases.append(("unknown section ID", unknown_section))

    too_many_sections = deepcopy(layout)
    only_page = too_many_sections["pages"][0]
    content = only_page["sections"][1]
    only_page["sections"] = (
        [only_page["sections"][0]]
        + [{**content, "id": f"content:{index}"} for index in range(25)]
        + [only_page["sections"][-1]]
    )
    too_many_sections["pages"] = [only_page]
    cases.append(("at most 24 sections", too_many_sections))

    return cases


@pytest.mark.parametrize("case_index", range(6))
def test_page_layout_rules_return_validation_errors(tmp_path: Path, case_index: int) -> None:
    with api_client(tmp_path) as client:
        project = create_project(client)
        _, layout = invalid_layouts(project)[case_index]
        response = client.patch(f"/api/v1/projects/{project['id']}", json={"pageLayout": layout})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_input"
    assert error["requestId"] == response.headers["x-request-id"]
    assert error["details"]


def test_unknown_catalog_id_and_extra_fields_are_rejected(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        project = create_project(client)
        unknown = client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"design": {"moodId": "unknown"}},
        )
        extra = client.post("/api/v1/projects", json={"ownerId": "frontend-user"})

    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "invalid_input"
    assert extra.status_code == 422
    assert extra.json()["error"]["details"][0]["field"] == "body.ownerId"


def test_list_projects_returns_owner_summaries_newest_first(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        first = create_project(client)
        second = create_project(client)
        client.patch(
            f"/api/v1/projects/{second['id']}",
            json={"business": {"companyName": "Northstar"}},
        )
        listed = client.get("/api/v1/projects")

    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    assert body[0]["id"] == second["id"]
    assert body[0]["companyName"] == "Northstar"
    assert body[0]["status"] == "draft"
    assert body[0]["latestBuildId"] is None
    assert body[0]["latestBuildStatus"] is None
    assert body[0]["previewUrl"] is None
    assert body[0]["downloadUrl"] is None
    assert body[1]["id"] == first["id"]
    assert body[1]["companyName"] == ""


def test_list_projects_includes_latest_build_summary(tmp_path: Path) -> None:
    with api_client(tmp_path) as client:
        project = create_project(client)
        database = client.app.state.database

        async def attach_completed_build() -> str:
            async with database.session() as session:
                from launchkit.persistence.repositories import PersistenceRepository

                repository = PersistenceRepository(session)
                record = await repository.get_project(project["id"], "user_testing")
                assert record is not None
                build = await repository.add_build(project_id=record.id, provider="v0")
                build.status = "completed"
                build.preview_url = "https://preview.example"
                record.latest_build_id = build.id
                record.status = "build_completed"
                await repository.commit()
                return build.id

        build_id = asyncio.run(attach_completed_build())
        listed = client.get("/api/v1/projects")

    assert listed.status_code == 200
    item = listed.json()[0]
    assert item["id"] == project["id"]
    assert item["latestBuildId"] == build_id
    assert item["latestBuildStatus"] == "completed"
    assert item["previewUrl"] == "https://preview.example"
    assert item["downloadUrl"] == f"/api/v1/builds/{build_id}/download"
