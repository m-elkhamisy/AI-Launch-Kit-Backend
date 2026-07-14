"""Persistence and durable worker characterization tests."""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.core.config import Settings
from launchkit.persistence import PersistenceRepository, create_database
from launchkit.persistence.base import Base
from launchkit.persistence.models import JobRecord
from launchkit.worker import Worker


def sqlite_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def test_initial_migration_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "migration.sqlite3"
    url = sqlite_url(database_path)
    monkeypatch.setenv("LAUNCHKIT_DATABASE_URL", url)
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)

    command.upgrade(config, "head")

    async def table_names() -> set[str]:
        database = create_database(Settings(environment="test", database_url=url))
        async with database.engine.connect() as connection:
            names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
        await database.close()
        return names

    assert {
        "alembic_version",
        "assets",
        "builds",
        "deployments",
        "idempotency_keys",
        "jobs",
        "mockups",
        "operations",
        "projects",
        "provider_references",
        "status_events",
        "webhook_deliveries",
    } <= asyncio.run(table_names())

    command.downgrade(config, "base")
    assert asyncio.run(table_names()) == {"alembic_version"}


def test_repository_scopes_projects_and_leases_jobs(tmp_path: Path) -> None:
    async def scenario() -> None:
        settings = Settings(environment="test", database_url=sqlite_url(tmp_path / "repo.sqlite3"))
        database = create_database(settings)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with database.session() as session:
            repository = PersistenceRepository(session)
            project = await repository.add_project(
                owner_id="owner-1",
                business={"companyName": "Northstar"},
                design={},
                page_layout={},
            )
            job = await repository.enqueue_job("profile.extract", {"projectId": project.id})
            await repository.commit()

        async with database.session() as session:
            repository = PersistenceRepository(session)
            assert await repository.get_project(project.id, "owner-1") is not None
            assert await repository.get_project(project.id, "owner-2") is None
            leased = await repository.lease_jobs(worker_id="worker-1", limit=10, lease_seconds=30)
            await repository.commit()

        assert [record.id for record in leased] == [job.id]
        assert leased[0].status == "leased"
        assert leased[0].attempts == 1
        await database.close()

    asyncio.run(scenario())


def test_worker_completes_registered_job(tmp_path: Path) -> None:
    handled: list[str] = []

    async def scenario() -> None:
        settings = Settings(
            environment="test",
            database_url=sqlite_url(tmp_path / "worker.sqlite3"),
            worker_batch_size=1,
        )

        async def handler(job: JobRecord, _: AsyncSession) -> None:
            handled.append(job.id)

        worker = Worker(settings, handlers={"test.job": handler})
        database = create_database(settings)
        async with database.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with database.session() as session:
            repository = PersistenceRepository(session)
            queued = await repository.enqueue_job("test.job", {})
            await repository.commit()

        assert await worker.run_once() == 1
        async with database.session() as session:
            completed = await session.scalar(select(JobRecord).where(JobRecord.id == queued.id))
            assert completed is not None
            assert completed.status == "completed"
            assert completed.lease_owner is None

        await worker.close()
        await database.close()

    asyncio.run(scenario())
    assert len(handled) == 1
