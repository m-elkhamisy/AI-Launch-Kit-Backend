"""Repository operations shared by API services and durable workers."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.persistence.models import JobRecord, ProjectRecord


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
