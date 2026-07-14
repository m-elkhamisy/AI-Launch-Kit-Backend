"""Durable profile and mockup API workflows with offline providers."""

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient
from PIL import Image

from launchkit.assets.storage import LocalAssetBlobStore
from launchkit.core.config import Settings
from launchkit.generation.briefing import BriefService
from launchkit.generation.html_generation import HtmlGenerationService
from launchkit.generation.mockups import MockupGenerationService
from launchkit.intake.models import OnboardingFormPatch
from launchkit.main import create_app
from launchkit.persistence import create_database
from launchkit.persistence.base import Base
from launchkit.profiles import ProfileExtractionService
from launchkit.profiles.models import ProfileDesignHints, ProfileFieldExtraction
from launchkit.worker import Worker
from launchkit.workflows.handlers import WorkflowJobHandlers


class FieldExtractorStub:
    async def extract_profile_fields(self, text: str) -> ProfileFieldExtraction:
        assert text
        return ProfileFieldExtraction(
            fields=OnboardingFormPatch(company_name="Profile Co", target_audience="Teams"),
            design_hints=ProfileDesignHints(tagline="Move clearly"),
        )


class VisualExtractorStub:
    async def extract_profile_image_fields(self, data_url: str) -> ProfileFieldExtraction:
        assert data_url.startswith("data:image/png;base64,")
        return ProfileFieldExtraction(
            fields=OnboardingFormPatch(company_name="Visual Co"),
            design_hints=ProfileDesignHints(cta="Explore"),
        )


class LabelerStub:
    async def label_image(self, data_url: str) -> str:
        assert data_url.startswith("data:image/")
        return "brand board"


class ShortGenerator:
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del prompt, system, max_tokens, model, temperature
        return "Clean industry direction"


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (4, 4), "white").save(buffer, format="PNG")
    return buffer.getvalue()


@contextmanager
def workflow_client(
    tmp_path: Path, *, configured: bool = True
) -> Iterator[tuple[TestClient, Settings, LocalAssetBlobStore]]:
    settings = Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'workflow.sqlite3').as_posix()}",
        local_data_dir=tmp_path / "data",
        openrouter_api_key="test" if configured else None,
        upload_max_bytes=1024,
    )
    database = create_database(settings)
    store = LocalAssetBlobStore(settings.local_data_dir / "assets")

    async def create_schema() -> None:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    with TestClient(create_app(settings, database, store)) as client:
        yield client, settings, store


def project(client: TestClient) -> dict[str, Any]:
    response = client.post("/api/v1/projects", json={})
    assert response.status_code == 201
    return cast(dict[str, Any], response.json())


def run_worker(settings: Settings, handlers: WorkflowJobHandlers) -> int:
    async def scenario() -> int:
        worker = Worker(settings, handlers=handlers.handlers)
        count = await worker.run_once()
        await worker.close()
        return count

    return asyncio.run(scenario())


def test_profile_upload_runs_durably_and_persists_extracted_assets(tmp_path: Path) -> None:
    with workflow_client(tmp_path) as (client, settings, store):
        created = project(client)
        queued = client.post(
            f"/api/v1/projects/{created['id']}/profile-extractions",
            files={"profile": ("brand.png", png_bytes(), "image/png")},
        )
        service = ProfileExtractionService(
            FieldExtractorStub(), LabelerStub(), VisualExtractorStub()
        )
        handlers = WorkflowJobHandlers(store, profile_service=service, mockup_service=None)

        assert queued.status_code == 202
        assert queued.json()["status"] == "queued"
        assert run_worker(settings, handlers) == 1

        operation = client.get(f"/api/v1/operations/{queued.json()['id']}")
        refreshed = client.get(f"/api/v1/projects/{created['id']}")
        image_asset = next(
            item for item in refreshed.json()["uploadedAssets"] if item["kind"] == "profile_image"
        )
        content = client.get(image_asset["previewUrl"])

    assert operation.json()["status"] == "completed"
    assert operation.json()["result"]["fields"]["companyName"] == "Visual Co"
    assert "data:" not in str(operation.json()["result"])
    assert refreshed.json()["business"]["companyName"] == "Visual Co"
    assert refreshed.json()["design"]["cta"] == "Explore"
    assert content.content == png_bytes()
    assert content.headers["x-content-type-options"] == "nosniff"


def test_mockup_generation_is_idempotent_selectable_and_sandboxed(tmp_path: Path) -> None:
    with workflow_client(tmp_path) as (client, settings, store):
        created = project(client)
        client.patch(
            f"/api/v1/projects/{created['id']}",
            json={"business": {"companyName": "Northstar"}},
        )
        headers = {"Idempotency-Key": "mockups-attempt-1"}
        first = client.post(f"/api/v1/projects/{created['id']}/mockups", headers=headers)
        duplicate = client.post(f"/api/v1/projects/{created['id']}/mockups", headers=headers)
        generator = ShortGenerator()
        mockup_service = MockupGenerationService(
            BriefService(generator), HtmlGenerationService(generator)
        )
        handlers = WorkflowJobHandlers(store, profile_service=None, mockup_service=mockup_service)

        assert first.status_code == 202
        assert duplicate.json()["id"] == first.json()["id"]
        assert run_worker(settings, handlers) == 1

        operation = client.get(f"/api/v1/operations/{first.json()['id']}")
        mockups = client.get(f"/api/v1/projects/{created['id']}/mockups")
        selected = client.put(
            f"/api/v1/projects/{created['id']}/selected-mockup",
            json={"mockupId": mockups.json()[0]["id"]},
        )
        preview = client.get(mockups.json()[0]["previewUrl"])
        refreshed = client.get(f"/api/v1/projects/{created['id']}")

    assert operation.json()["status"] == "completed"
    assert len(mockups.json()) == 3
    assert selected.status_code == 200
    assert refreshed.json()["selectedMockupId"] == selected.json()["id"]
    assert preview.text.startswith("<!DOCTYPE html>")
    assert preview.headers["content-security-policy"].startswith("sandbox allow-scripts")


def test_upload_errors_and_missing_provider_are_controlled(tmp_path: Path) -> None:
    with workflow_client(tmp_path, configured=False) as (client, _, _):
        created = project(client)
        unconfigured = client.post(
            f"/api/v1/projects/{created['id']}/profile-extractions",
            files={"profile": ("profile.txt", b"Company", "text/plain")},
        )
        invalid = client.post(
            f"/api/v1/projects/{created['id']}/profile-extractions",
            files={"profile": ("profile.png", b"bad", "image/png")},
        )

    assert unconfigured.status_code == 503
    assert unconfigured.json()["error"]["code"] == "provider_configuration_missing"
    assert invalid.status_code == 422


def test_upload_validation_returns_422_and_413(tmp_path: Path) -> None:
    with workflow_client(tmp_path) as (client, _, _):
        created = project(client)
        malformed = client.post(
            f"/api/v1/projects/{created['id']}/profile-extractions",
            files={"profile": ("profile.png", b"bad", "image/png")},
        )
        oversized = client.post(
            f"/api/v1/projects/{created['id']}/profile-extractions",
            files={"profile": ("profile.txt", b"x" * 1025, "text/plain")},
        )

    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "invalid_upload"
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "upload_too_large"
