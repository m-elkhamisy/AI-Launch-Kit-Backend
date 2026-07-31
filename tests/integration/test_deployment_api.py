"""Durable Vercel deployment and signed webhook lifecycle."""

import asyncio
import hashlib
import hmac
import json
import zipfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from launchkit.assets.storage import LocalAssetBlobStore
from launchkit.core.config import Settings
from launchkit.core.exceptions import ProviderError
from launchkit.deployment.handlers import DeploymentJobHandlers
from launchkit.deployment.models import DeploymentFile, VercelDeployment
from launchkit.main import create_app
from launchkit.persistence import PersistenceRepository, create_database
from launchkit.persistence.base import Base
from launchkit.worker import Worker


class VercelStub:
    def __init__(self, error: ProviderError | None = None) -> None:
        self.error = error
        self.files: list[DeploymentFile] = []
        self.creates = 0

    async def create_deployment(
        self, chat_id: str, files: Sequence[DeploymentFile]
    ) -> VercelDeployment:
        assert chat_id.startswith("dep_")
        self.creates += 1
        self.files = list(files)
        if self.error:
            raise self.error
        return VercelDeployment(
            project_id="vercel-project-private",
            deployment_id="dpl_private",
            url="northstar.vercel.app",
        )

    async def create_transfer_code(self, project_id_or_name: str) -> str:
        assert project_id_or_name == "vercel-project-private"
        return "private-transfer-code"


@contextmanager
def deployment_client(
    tmp_path: Path, *, configured: bool = True
) -> Iterator[tuple[TestClient, Settings, LocalAssetBlobStore]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        environment="test",
        auth_mode="testing",
        database_url=f"sqlite+aiosqlite:///{(tmp_path / 'deployment.sqlite3').as_posix()}",
        local_data_dir=tmp_path / "data",
        vercel_token="vercel" if configured else None,
        vercel_webhook_secret="webhook-secret",
        claim_return_url="https://launchkit.example/deployment-complete",
    )
    database = create_database(settings)
    store = LocalAssetBlobStore(settings.local_data_dir / "assets")

    async def create_schema() -> None:
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    with TestClient(create_app(settings, database, store)) as client:
        yield client, settings, store


def archive_bytes() -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("package.json", '{"scripts":{"build":"next build"}}')
        archive.writestr("app/page.tsx", "export default function Page(){return <h1>Hi</h1>}")
    return output.getvalue()


def create_completed_build(
    client: TestClient, settings: Settings, store: LocalAssetBlobStore
) -> tuple[str, str]:
    # One website per owner: reuse an existing draft when the test already created one.
    listed = client.get("/api/v1/projects")
    assert listed.status_code == 200
    projects = listed.json()
    if projects:
        project_id = cast(str, projects[0]["id"])
        patched = client.patch(
            f"/api/v1/projects/{project_id}",
            json={"business": {"companyName": "Northstar"}},
        )
        assert patched.status_code == 200
    else:
        response = client.post("/api/v1/projects", json={"business": {"companyName": "Northstar"}})
        assert response.status_code == 201
        project_id = cast(str, response.json()["id"])

    async def scenario() -> str:
        content = archive_bytes()
        storage_key = f"projects/{project_id}/builds/site.zip"
        await store.put(storage_key, content, "application/zip")
        database = create_database(settings)
        async with database.session() as session:
            repository = PersistenceRepository(session)
            asset = await repository.add_asset(
                project_id=project_id,
                kind="build_archive",
                storage_key=storage_key,
                filename="site.zip",
                label="Generated website",
                content_type="application/zip",
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
            )
            build = await repository.add_build(project_id=project_id, provider="v0")
            build.status = "completed"
            build.stage = "completed"
            build.message = "Website generation completed"
            build.archive_asset_id = asset.id
            await repository.commit()
        await database.close()
        return build.id

    return project_id, asyncio.run(scenario())


def run_worker(settings: Settings, handlers: DeploymentJobHandlers) -> int:
    async def scenario() -> int:
        worker = Worker(settings, handlers=handlers.handlers)
        count = await worker.run_once()
        await worker.close()
        return count

    return asyncio.run(scenario())


def signed_payload(payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(b"webhook-secret", raw, hashlib.sha1).hexdigest()
    return raw, {"Content-Type": "application/json", "x-vercel-signature": signature}


def test_deployment_becomes_claimable_and_accepts_signed_webhooks(tmp_path: Path) -> None:
    with deployment_client(tmp_path) as (client, settings, store):
        project_id, build_id = create_completed_build(client, settings, store)
        headers = {"Idempotency-Key": "deploy-1"}
        queued = client.post(f"/api/v1/builds/{build_id}/deployments", json={}, headers=headers)
        duplicate = client.post(f"/api/v1/builds/{build_id}/deployments", json={}, headers=headers)
        active = client.post(
            f"/api/v1/builds/{build_id}/deployments",
            json={},
            headers={"Idempotency-Key": "deploy-2"},
        )
        vercel = VercelStub()
        handlers = DeploymentJobHandlers(settings, store, vercel=vercel)
        assert run_worker(settings, handlers) == 1
        ready = client.get(f"/api/v1/deployments/{queued.json()['id']}")
        project = client.get(f"/api/v1/projects/{project_id}")

        payload = {
            "id": "vercel-event-1",
            "type": "deployment.succeeded",
            "payload": {"deployment": {"id": "dpl_private", "url": "updated.vercel.app"}},
        }
        raw, signed_headers = signed_payload(payload)
        hook = client.post("/api/v1/webhooks/vercel", content=raw, headers=signed_headers)
        hook_duplicate = client.post("/api/v1/webhooks/vercel", content=raw, headers=signed_headers)
        refreshed = client.get(f"/api/v1/deployments/{queued.json()['id']}")
        error_payload = {
            "id": "vercel-event-2",
            "type": "deployment.error",
            "payload": {"deployment": {"id": "dpl_private"}},
        }
        raw, signed_headers = signed_payload(error_payload)
        error_hook = client.post("/api/v1/webhooks/vercel", content=raw, headers=signed_headers)
        failed = client.get(f"/api/v1/deployments/{queued.json()['id']}")

    assert queued.status_code == 202
    assert duplicate.json()["id"] == queued.json()["id"]
    assert active.json()["id"] == queued.json()["id"]
    assert ready.json()["status"] == "ready_to_claim"
    assert ready.json()["liveUrl"] == "https://northstar.vercel.app"
    assert "private-transfer-code" in ready.json()["claimUrl"]
    assert ready.json()["claimExpiresAt"] is not None
    assert "dpl_private" not in ready.text
    assert "vercel-project-private" not in ready.text
    assert project.json()["latestDeploymentId"] == queued.json()["id"]
    assert vercel.creates == 1
    assert {item.file for item in vercel.files} == {"package.json", "app/page.tsx"}
    assert hook.json()["correlated"] is True
    assert hook_duplicate.json()["duplicate"] is True
    assert refreshed.json()["liveUrl"] == "https://updated.vercel.app"
    assert error_hook.json()["correlated"] is True
    assert failed.json()["status"] == "failed"


def test_deployment_guards_and_provider_failure_are_safe(tmp_path: Path) -> None:
    with deployment_client(tmp_path) as (client, settings, store):
        missing = client.post(
            "/api/v1/builds/missing/deployments",
            json={},
            headers={"Idempotency-Key": "missing"},
        )
        project = client.post("/api/v1/projects", json={}).json()

        async def incomplete_build() -> str:
            database = create_database(settings)
            async with database.session() as session:
                repository = PersistenceRepository(session)
                build = await repository.add_build(project_id=project["id"], provider="v0")
                await repository.commit()
            await database.close()
            return build.id

        build_id = asyncio.run(incomplete_build())
        incomplete = client.post(
            f"/api/v1/builds/{build_id}/deployments",
            json={},
            headers={"Idempotency-Key": "incomplete"},
        )
        _, completed_id = create_completed_build(client, settings, store)
        queued = client.post(
            f"/api/v1/builds/{completed_id}/deployments",
            json={},
            headers={"Idempotency-Key": "provider-error"},
        )
        vercel = VercelStub(ProviderError("private Vercel response", retryable=True))
        assert run_worker(settings, DeploymentJobHandlers(settings, store, vercel=vercel)) == 1
        failed = client.get(f"/api/v1/deployments/{queued.json()['id']}")
        missing_read = client.get("/api/v1/deployments/missing")

    assert missing.status_code == 404
    assert incomplete.status_code == 409
    assert failed.json()["status"] == "failed"
    assert "private Vercel response" not in failed.text
    assert missing_read.status_code == 404

    with deployment_client(tmp_path / "unconfigured", configured=False) as (
        client,
        settings,
        store,
    ):
        _, build_id = create_completed_build(client, settings, store)
        unconfigured = client.post(
            f"/api/v1/builds/{build_id}/deployments",
            json={},
            headers={"Idempotency-Key": "unconfigured"},
        )
    assert unconfigured.status_code == 503


def test_vercel_webhook_signature_payload_and_correlation_errors(tmp_path: Path) -> None:
    with deployment_client(tmp_path) as (client, settings, store):
        bad_signature = client.post(
            "/api/v1/webhooks/vercel",
            content=b"{}",
            headers={
                "Content-Type": "application/json",
                "x-vercel-signature": "wrong",
            },
        )
        unknown_payload = {
            "id": "unknown",
            "type": "deployment.error",
            "payload": {"deployment": {"id": "dpl_unknown"}},
        }
        raw, headers = signed_payload(unknown_payload)
        unknown = client.post("/api/v1/webhooks/vercel", content=raw, headers=headers)
        missing_id_payload = {"id": "missing", "type": "deployment.error", "payload": {}}
        raw, headers = signed_payload(missing_id_payload)
        missing_id = client.post("/api/v1/webhooks/vercel", content=raw, headers=headers)
        ignored_payload = {"id": "ignored", "type": "project.created", "payload": {}}
        raw, headers = signed_payload(ignored_payload)
        ignored = client.post("/api/v1/webhooks/vercel", content=raw, headers=headers)
        del settings, store

    assert bad_signature.status_code == 401
    assert unknown.json()["status"] == "ignored"
    assert missing_id.status_code == 400
    assert ignored.json()["status"] == "ignored"
