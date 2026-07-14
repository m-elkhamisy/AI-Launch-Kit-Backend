"""Repository operations shared by API services and durable workers."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.persistence.models import (
    AssetRecord,
    IdempotencyRecord,
    JobRecord,
    MockupRecord,
    OperationRecord,
    ProjectRecord,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class PersistenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_project(
        self,
        *,
        owner_id: str,
        business: dict[str, Any],
        design: dict[str, Any],
        page_layout: dict[str, Any],
    ) -> ProjectRecord:
        record = ProjectRecord(
            id=new_id("prj"),
            owner_id=owner_id,
            business=business,
            design=design,
            page_layout=page_layout,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_project(self, project_id: str, owner_id: str) -> ProjectRecord | None:
        records = await self._session.scalars(
            select(ProjectRecord).where(
                ProjectRecord.id == project_id, ProjectRecord.owner_id == owner_id
            )
        )
        return records.one_or_none()

    async def enqueue_job(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        operation_id: str | None = None,
        available_at: datetime | None = None,
    ) -> JobRecord:
        record = JobRecord(
            id=new_id("job"),
            operation_id=operation_id,
            kind=kind,
            payload=payload,
            available_at=available_at or datetime.now(UTC),
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def add_asset(
        self,
        *,
        project_id: str,
        kind: str,
        storage_key: str,
        filename: str,
        label: str,
        content_type: str,
        size: int,
        sha256: str,
    ) -> AssetRecord:
        record = AssetRecord(
            id=new_id("ast"),
            project_id=project_id,
            kind=kind,
            storage_key=storage_key,
            filename=filename,
            label=label,
            content_type=content_type,
            size=size,
            sha256=sha256,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_asset(self, asset_id: str, owner_id: str) -> AssetRecord | None:
        records = await self._session.scalars(
            select(AssetRecord)
            .join(ProjectRecord, AssetRecord.project_id == ProjectRecord.id)
            .where(AssetRecord.id == asset_id, ProjectRecord.owner_id == owner_id)
        )
        return records.one_or_none()

    async def list_assets(self, project_id: str) -> Sequence[AssetRecord]:
        records = await self._session.scalars(
            select(AssetRecord)
            .where(AssetRecord.project_id == project_id)
            .order_by(AssetRecord.created_at, AssetRecord.id)
        )
        return records.all()

    async def add_operation(self, *, project_id: str, kind: str) -> OperationRecord:
        record = OperationRecord(id=new_id("op"), project_id=project_id, kind=kind)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_operation(self, operation_id: str, owner_id: str) -> OperationRecord | None:
        records = await self._session.scalars(
            select(OperationRecord)
            .join(ProjectRecord, OperationRecord.project_id == ProjectRecord.id)
            .where(OperationRecord.id == operation_id, ProjectRecord.owner_id == owner_id)
        )
        return records.one_or_none()

    async def add_mockup(
        self,
        *,
        project_id: str,
        generation: int,
        ordinal: int,
        label: str,
        direction: str,
        artifact_asset_id: str,
    ) -> MockupRecord:
        record = MockupRecord(
            id=new_id("mkp"),
            project_id=project_id,
            generation=generation,
            ordinal=ordinal,
            label=label,
            direction=direction,
            artifact_asset_id=artifact_asset_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_mockups(self, project_id: str) -> Sequence[MockupRecord]:
        records = await self._session.scalars(
            select(MockupRecord)
            .where(MockupRecord.project_id == project_id)
            .order_by(MockupRecord.generation.desc(), MockupRecord.ordinal)
        )
        return records.all()

    async def get_mockup(self, mockup_id: str, project_id: str) -> MockupRecord | None:
        records = await self._session.scalars(
            select(MockupRecord).where(
                MockupRecord.id == mockup_id, MockupRecord.project_id == project_id
            )
        )
        return records.one_or_none()

    async def next_mockup_generation(self, project_id: str) -> int:
        latest = await self._session.scalar(
            select(func.max(MockupRecord.generation)).where(MockupRecord.project_id == project_id)
        )
        return int(latest or 0) + 1

    async def get_idempotency(
        self, *, owner_id: str, scope: str, key_hash: str
    ) -> IdempotencyRecord | None:
        records = await self._session.scalars(
            select(IdempotencyRecord).where(
                IdempotencyRecord.owner_id == owner_id,
                IdempotencyRecord.scope == scope,
                IdempotencyRecord.key_hash == key_hash,
            )
        )
        return records.one_or_none()

    async def add_idempotency(
        self,
        *,
        owner_id: str,
        scope: str,
        key_hash: str,
        request_hash: str,
        resource_type: str,
        resource_id: str,
    ) -> IdempotencyRecord:
        record = IdempotencyRecord(
            id=new_id("idem"),
            owner_id=owner_id,
            scope=scope,
            key_hash=key_hash,
            request_hash=request_hash,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def lease_jobs(
        self,
        *,
        worker_id: str,
        limit: int,
        lease_seconds: int,
    ) -> Sequence[JobRecord]:
        now = datetime.now(UTC)
        query: Select[tuple[JobRecord]] = (
            select(JobRecord)
            .where(
                JobRecord.available_at <= now,
                or_(
                    JobRecord.status == "queued",
                    and_(JobRecord.status == "leased", JobRecord.leased_until < now),
                ),
            )
            .order_by(JobRecord.available_at, JobRecord.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list((await self._session.scalars(query)).all())
        for job in jobs:
            job.status = "leased"
            job.lease_owner = worker_id
            job.leased_until = now + timedelta(seconds=lease_seconds)
            job.attempts += 1
        await self._session.flush()
        return jobs

    async def commit(self) -> None:
        await self._session.commit()

    async def refresh(self, record: object) -> None:
        await self._session.refresh(record)
