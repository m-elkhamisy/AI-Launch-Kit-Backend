"""Deployment service readiness, idempotency, and ownership rules."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, DomainError
from launchkit.deployment.models import DeploymentCreate, DeploymentView
from launchkit.deployment.service import DeploymentNotFoundError, DeploymentService
from launchkit.persistence.models import BuildRecord, DeploymentRecord, ProjectRecord
from launchkit.persistence.repositories import PersistenceRepository


class DeploymentRepositoryStub:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.build: BuildRecord | None = BuildRecord(
            id="build-1",
            project_id="project-1",
            provider="v0",
            status="completed",
            stage="completed",
            message="Complete",
            archive_asset_id="asset-1",
            warnings=[],
            created_at=now,
            updated_at=now,
        )
        self.project = ProjectRecord(
            id="project-1",
            owner_id="owner-1",
            status="build_completed",
            business={},
            design={},
            page_layout={},
            created_at=now,
            updated_at=now,
        )
        self.deployment: DeploymentRecord | None = None
        self.active: DeploymentRecord | None = None
        self.idempotency: Any | None = None
        self.jobs: list[tuple[str, dict[str, str]]] = []
        self.commits = 0

    async def get_build(self, build_id: str, owner_id: str) -> BuildRecord | None:
        del build_id, owner_id
        return self.build

    async def get_idempotency(self, **values: str) -> Any | None:
        del values
        return self.idempotency

    async def get_deployment(self, deployment_id: str, owner_id: str) -> DeploymentRecord | None:
        del deployment_id, owner_id
        return self.deployment

    async def find_active_deployment(self, build_id: str) -> DeploymentRecord | None:
        del build_id
        return self.active

    async def add_deployment(self, *, build_id: str) -> DeploymentRecord:
        now = datetime.now(UTC)
        self.deployment = DeploymentRecord(
            id="deployment-1",
            build_id=build_id,
            status="queued",
            public_message="Deployment queued",
            created_at=now,
            updated_at=now,
        )
        return self.deployment

    async def add_status_event(self, **event: Any) -> None:
        del event

    async def enqueue_job(self, kind: str, payload: dict[str, str]) -> None:
        self.jobs.append((kind, payload))

    async def add_idempotency(self, **values: str) -> None:
        self.idempotency = SimpleNamespace(
            request_hash=values["request_hash"], resource_id=values["resource_id"]
        )

    async def get_project_for_build(self, build_id: str) -> ProjectRecord:
        del build_id
        return self.project

    async def commit(self) -> None:
        self.commits += 1


def deployment_service(
    repository: DeploymentRepositoryStub, *, configured: bool = True
) -> DeploymentService:
    return DeploymentService(
        cast(PersistenceRepository, repository),
        "owner-1",
        Settings(environment="test", vercel_token="token" if configured else None),
    )


def start(
    repository: DeploymentRepositoryStub,
    key: str = "deployment-key",
    request: DeploymentCreate | None = None,
) -> DeploymentView:
    return asyncio.run(
        deployment_service(repository).start("build-1", request or DeploymentCreate(), key)
    )


def test_start_enforces_build_configuration_and_readiness() -> None:
    repository = DeploymentRepositoryStub()
    repository.build = None
    with pytest.raises(DeploymentNotFoundError, match="Build not found"):
        start(repository)

    repository = DeploymentRepositoryStub()
    with pytest.raises(ConfigurationError, match="Vercel"):
        asyncio.run(
            deployment_service(repository, configured=False).start(
                "build-1", DeploymentCreate(), "key"
            )
        )

    assert repository.build is not None
    repository.build.status = "running"
    with pytest.raises(DomainError, match="Complete"):
        start(repository)
    repository.build.status = "completed"
    with pytest.raises(DomainError, match="Only Vercel"):
        start(repository, request=DeploymentCreate(provider="other"))
    with pytest.raises(DomainError, match="Idempotency-Key"):
        start(repository, " ")


def test_start_persists_and_reuses_deployments() -> None:
    repository = DeploymentRepositoryStub()
    created = start(repository)
    repeated = start(repository)

    assert created.id == repeated.id == "deployment-1"
    assert repository.jobs == [("deployment.create", {"deploymentId": "deployment-1"})]
    assert repository.project.latest_deployment_id == "deployment-1"
    assert repository.project.status == "deployment_queued"
    assert repository.commits == 1

    assert repository.idempotency is not None
    repository.idempotency.request_hash = "different"
    with pytest.raises(DomainError, match="different deployment"):
        start(repository)


def test_start_reuses_active_and_rejects_dangling_idempotency() -> None:
    repository = DeploymentRepositoryStub()
    created = start(repository)
    assert repository.deployment is not None
    repository.idempotency = None
    repository.active = repository.deployment
    assert start(repository, "new-key").id == created.id

    repository.active = None
    start(repository, "stored-key")
    repository.deployment = None
    with pytest.raises(DeploymentNotFoundError, match="Deployment not found"):
        start(repository, "stored-key")


def test_get_enforces_ownership() -> None:
    repository = DeploymentRepositoryStub()
    service = deployment_service(repository)
    with pytest.raises(DeploymentNotFoundError, match="Deployment not found"):
        asyncio.run(service.get("missing"))
    created = start(repository)
    assert asyncio.run(service.get(created.id)).id == created.id
