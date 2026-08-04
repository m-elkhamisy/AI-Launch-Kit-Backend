"""Repository operations shared by API services and durable workers."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.persistence.models import (
    AssetRecord,
    BuildRecord,
    DeploymentRecord,
    IdempotencyRecord,
    JobRecord,
    MockupRecord,
    OperationRecord,
    ProjectRecord,
    ProviderReferenceRecord,
    StatusEventRecord,
    UserRecord,
    WebhookDeliveryRecord,
    utc_now,
)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class PersistenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_user(
        self,
        *,
        user_id: str,
        email: str | None = None,
        full_name: str | None = None,
        phone: str | None = None,
        company_name: str | None = None,
        role: str | None = None,
        pool: str | None = None,
        profile: dict[str, Any] | None = None,
    ) -> UserRecord:
        """Create or refresh the login record for an authenticated user."""

        record = await self._session.get(UserRecord, user_id)
        if record is None:
            record = UserRecord(id=user_id)
            self._session.add(record)
        record.email = email or record.email
        record.full_name = full_name or record.full_name
        record.phone = phone or record.phone
        record.company_name = company_name or record.company_name
        record.role = role or record.role
        record.pool = pool or record.pool
        if profile is not None:
            record.profile = profile
        record.last_login_at = utc_now()
        await self._session.flush()
        return record

    async def get_user(self, user_id: str) -> UserRecord | None:
        return await self._session.get(UserRecord, user_id)

    async def count_owner_website_builds(self, owner_id: str) -> int:
        """Count non-failed builds across all of the owner's projects."""

        result = await self._session.scalar(
            select(func.count(BuildRecord.id))
            .join(ProjectRecord, BuildRecord.project_id == ProjectRecord.id)
            .where(ProjectRecord.owner_id == owner_id, BuildRecord.status != "failed")
        )
        return int(result or 0)

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

    async def list_projects(self, owner_id: str) -> Sequence[ProjectRecord]:
        records = await self._session.scalars(
            select(ProjectRecord)
            .where(ProjectRecord.owner_id == owner_id)
            .order_by(ProjectRecord.updated_at.desc())
        )
        return records.all()

    async def get_builds_by_ids(
        self, build_ids: Sequence[str], owner_id: str
    ) -> Sequence[BuildRecord]:
        if not build_ids:
            return []
        records = await self._session.scalars(
            select(BuildRecord)
            .join(ProjectRecord, BuildRecord.project_id == ProjectRecord.id)
            .where(BuildRecord.id.in_(tuple(build_ids)), ProjectRecord.owner_id == owner_id)
        )
        return records.all()

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

    async def get_asset_for_project(self, asset_id: str, project_id: str) -> AssetRecord | None:
        records = await self._session.scalars(
            select(AssetRecord).where(
                AssetRecord.id == asset_id, AssetRecord.project_id == project_id
            )
        )
        return records.one_or_none()

    async def list_assets(self, project_id: str) -> Sequence[AssetRecord]:
        records = await self._session.scalars(
            select(AssetRecord)
            .where(AssetRecord.project_id == project_id)
            .order_by(AssetRecord.created_at, AssetRecord.id)
        )
        return records.all()

    async def delete_asset(self, asset: AssetRecord) -> None:
        await self._session.delete(asset)
        await self._session.flush()

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

    async def add_build(self, *, project_id: str, provider: str) -> BuildRecord:
        record = BuildRecord(id=new_id("bld"), project_id=project_id, provider=provider)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_build(self, build_id: str, owner_id: str) -> BuildRecord | None:
        records = await self._session.scalars(
            select(BuildRecord)
            .join(ProjectRecord, BuildRecord.project_id == ProjectRecord.id)
            .where(BuildRecord.id == build_id, ProjectRecord.owner_id == owner_id)
        )
        return records.one_or_none()

    async def get_project_for_build(self, build_id: str) -> ProjectRecord | None:
        records = await self._session.scalars(
            select(ProjectRecord)
            .join(BuildRecord, BuildRecord.project_id == ProjectRecord.id)
            .where(BuildRecord.id == build_id)
        )
        return records.one_or_none()

    async def find_active_build(self, project_id: str) -> BuildRecord | None:
        records = await self._session.scalars(
            select(BuildRecord)
            .where(
                BuildRecord.project_id == project_id,
                BuildRecord.status.in_(("queued", "submitting", "running", "processing_result")),
            )
            .order_by(BuildRecord.created_at.desc())
            .limit(1)
        )
        return records.one_or_none()

    async def add_deployment(self, *, build_id: str) -> DeploymentRecord:
        record = DeploymentRecord(id=new_id("dep"), build_id=build_id)
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_deployment(self, deployment_id: str, owner_id: str) -> DeploymentRecord | None:
        records = await self._session.scalars(
            select(DeploymentRecord)
            .join(BuildRecord, DeploymentRecord.build_id == BuildRecord.id)
            .join(ProjectRecord, BuildRecord.project_id == ProjectRecord.id)
            .where(DeploymentRecord.id == deployment_id, ProjectRecord.owner_id == owner_id)
        )
        return records.one_or_none()

    async def find_active_deployment(self, build_id: str) -> DeploymentRecord | None:
        records = await self._session.scalars(
            select(DeploymentRecord)
            .where(
                DeploymentRecord.build_id == build_id,
                DeploymentRecord.status.in_(("queued", "creating", "building", "ready_to_claim")),
            )
            .order_by(DeploymentRecord.created_at.desc())
            .limit(1)
        )
        return records.one_or_none()

    async def find_deployment_by_provider_reference(
        self, *, provider: str, reference_type: str, reference_value: str
    ) -> DeploymentRecord | None:
        records = await self._session.scalars(
            select(DeploymentRecord)
            .join(
                ProviderReferenceRecord,
                and_(
                    ProviderReferenceRecord.resource_type == "deployment",
                    ProviderReferenceRecord.resource_id == DeploymentRecord.id,
                ),
            )
            .where(
                ProviderReferenceRecord.provider == provider,
                ProviderReferenceRecord.reference_type == reference_type,
                ProviderReferenceRecord.reference_value == reference_value,
            )
        )
        return records.one_or_none()

    async def add_provider_reference(
        self,
        *,
        resource_type: str,
        resource_id: str,
        provider: str,
        reference_type: str,
        reference_value: str,
    ) -> ProviderReferenceRecord:
        record = ProviderReferenceRecord(
            id=new_id("ref"),
            resource_type=resource_type,
            resource_id=resource_id,
            provider=provider,
            reference_type=reference_type,
            reference_value=reference_value,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_provider_reference(
        self, *, resource_type: str, resource_id: str, provider: str, reference_type: str
    ) -> ProviderReferenceRecord | None:
        records = await self._session.scalars(
            select(ProviderReferenceRecord).where(
                ProviderReferenceRecord.resource_type == resource_type,
                ProviderReferenceRecord.resource_id == resource_id,
                ProviderReferenceRecord.provider == provider,
                ProviderReferenceRecord.reference_type == reference_type,
            )
        )
        return records.one_or_none()

    async def find_build_by_provider_reference(
        self, *, provider: str, reference_type: str, reference_value: str
    ) -> BuildRecord | None:
        records = await self._session.scalars(
            select(BuildRecord)
            .join(
                ProviderReferenceRecord,
                and_(
                    ProviderReferenceRecord.resource_type == "build",
                    ProviderReferenceRecord.resource_id == BuildRecord.id,
                ),
            )
            .where(
                ProviderReferenceRecord.provider == provider,
                ProviderReferenceRecord.reference_type == reference_type,
                ProviderReferenceRecord.reference_value == reference_value,
            )
        )
        return records.one_or_none()

    async def add_status_event(
        self,
        *,
        resource_type: str,
        resource_id: str,
        from_status: str | None,
        to_status: str,
        stage: str,
        message: str,
    ) -> StatusEventRecord:
        latest = await self._session.scalar(
            select(func.max(StatusEventRecord.sequence)).where(
                StatusEventRecord.resource_type == resource_type,
                StatusEventRecord.resource_id == resource_id,
            )
        )
        record = StatusEventRecord(
            id=new_id("evt"),
            resource_type=resource_type,
            resource_id=resource_id,
            sequence=int(latest or 0) + 1,
            from_status=from_status,
            to_status=to_status,
            stage=stage,
            message=message,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def list_status_events(
        self, *, resource_type: str, resource_id: str, after_sequence: int = 0
    ) -> Sequence[StatusEventRecord]:
        records = await self._session.scalars(
            select(StatusEventRecord)
            .where(
                StatusEventRecord.resource_type == resource_type,
                StatusEventRecord.resource_id == resource_id,
                StatusEventRecord.sequence > after_sequence,
            )
            .order_by(StatusEventRecord.sequence)
        )
        return records.all()

    async def add_webhook_delivery(
        self,
        *,
        provider: str,
        delivery_key: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> WebhookDeliveryRecord:
        record = WebhookDeliveryRecord(
            id=new_id("whd"),
            provider=provider,
            delivery_key=delivery_key,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_webhook_delivery(
        self, *, provider: str, delivery_key: str
    ) -> WebhookDeliveryRecord | None:
        records = await self._session.scalars(
            select(WebhookDeliveryRecord).where(
                WebhookDeliveryRecord.provider == provider,
                WebhookDeliveryRecord.delivery_key == delivery_key,
            )
        )
        return records.one_or_none()

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
