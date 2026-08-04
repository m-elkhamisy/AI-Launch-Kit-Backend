"""Create and inspect durable profile and mockup workflows."""

import hashlib
import json
import uuid
from collections.abc import Sequence

from launchkit.assets import AssetBlobStore, validate_brand_upload, validate_profile_upload
from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, DomainError
from launchkit.persistence.models import AssetRecord, MockupRecord, OperationRecord, ProjectRecord
from launchkit.persistence.repositories import PersistenceRepository
from launchkit.workflows.models import AssetView, MockupView, OperationView

MAX_BRAND_DOCUMENTS = 5


class WorkflowNotFoundError(DomainError):
    """Raised when an operation, asset, or mockup is not owned by the current user."""


class IdempotencyConflictError(DomainError):
    """Raised when one key is reused for a different request."""


class WorkflowService:
    def __init__(
        self,
        repository: PersistenceRepository,
        owner_id: str,
        settings: Settings,
        asset_store: AssetBlobStore,
    ) -> None:
        self._repository = repository
        self._owner_id = owner_id
        self._settings = settings
        self._asset_store = asset_store

    async def start_profile_extraction(
        self, project_id: str, filename: str, content_type: str, content: bytes
    ) -> OperationView:
        await self._project(project_id)
        upload = validate_profile_upload(
            filename, content_type, content, max_bytes=self._settings.upload_max_bytes
        )
        if self._settings.openrouter_api_key is None:
            raise ConfigurationError("OpenRouter is required for profile extraction")
        digest = hashlib.sha256(upload.content).hexdigest()
        storage_key = f"projects/{project_id}/profiles/{uuid.uuid4().hex}-{upload.filename}"
        await self._asset_store.put(storage_key, upload.content, upload.content_type)
        asset = await self._repository.add_asset(
            project_id=project_id,
            kind="profile_source",
            storage_key=storage_key,
            filename=upload.filename,
            label="Company profile",
            content_type=upload.content_type,
            size=len(upload.content),
            sha256=digest,
        )
        operation = await self._repository.add_operation(
            project_id=project_id, kind="profile_extraction"
        )
        await self._repository.enqueue_job(
            "profile.extract",
            {"projectId": project_id, "assetId": asset.id},
            operation_id=operation.id,
        )
        await self._repository.commit()
        return operation_view(operation)

    async def start_profile_extraction_from_asset(
        self, project_id: str, asset_id: str
    ) -> OperationView:
        """Queue AI extraction against an already-stored brand document."""

        await self._project(project_id)
        if self._settings.openrouter_api_key is None:
            raise ConfigurationError("OpenRouter is required for profile extraction")
        asset = await self._repository.get_asset_for_project(asset_id, project_id)
        if asset is None or asset.kind != "profile_source":
            raise WorkflowNotFoundError("Brand document not found")
        operation = await self._repository.add_operation(
            project_id=project_id, kind="profile_extraction"
        )
        await self._repository.enqueue_job(
            "profile.extract",
            {"projectId": project_id, "assetId": asset.id},
            operation_id=operation.id,
        )
        await self._repository.commit()
        return operation_view(operation)

    async def upload_brand_asset(
        self,
        project_id: str,
        *,
        kind: str,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> AssetView:
        """Persist a Business-step logo or supporting document without AI extraction."""

        await self._project(project_id)
        if kind not in {"logo", "document"}:
            raise DomainError("Brand asset kind must be logo or document.")
        upload = validate_brand_upload(filename, content_type, content, kind=kind)
        assets = list(await self._repository.list_assets(project_id))
        if kind == "document":
            document_count = sum(1 for asset in assets if asset.kind == "profile_source")
            if document_count >= MAX_BRAND_DOCUMENTS:
                raise DomainError(f"Upload at most {MAX_BRAND_DOCUMENTS} brand documents.")
        if kind == "logo":
            for existing in assets:
                if existing.kind == "profile_image" and "logo" in existing.label.lower():
                    await self._repository.delete_asset(existing)
                    break

        folder = "logos" if kind == "logo" else "profiles"
        storage_key = f"projects/{project_id}/{folder}/{uuid.uuid4().hex}-{upload.filename}"
        await self._asset_store.put(storage_key, upload.content, upload.content_type)
        asset_kind = "profile_image" if kind == "logo" else "profile_source"
        label = "logo" if kind == "logo" else "Brand document"
        record = await self._repository.add_asset(
            project_id=project_id,
            kind=asset_kind,
            storage_key=storage_key,
            filename=upload.filename,
            label=label,
            content_type=upload.content_type,
            size=len(upload.content),
            sha256=hashlib.sha256(upload.content).hexdigest(),
        )
        await self._repository.commit()
        return asset_view(record)

    async def delete_brand_asset(self, project_id: str, asset_id: str) -> None:
        await self._project(project_id)
        asset = await self._repository.get_asset_for_project(asset_id, project_id)
        if asset is None:
            raise WorkflowNotFoundError("Asset not found")
        if asset.kind not in {"profile_image", "profile_source"}:
            raise DomainError("Only brand upload assets can be removed.")
        await self._repository.delete_asset(asset)
        await self._repository.commit()

    async def start_mockups(self, project_id: str, idempotency_key: str) -> OperationView:
        project = await self._project(project_id)
        if self._settings.openrouter_api_key is None:
            raise ConfigurationError("OpenRouter is required for mockup generation")
        normalized_key = idempotency_key.strip()
        if not normalized_key or len(normalized_key) > 200:
            raise DomainError("A valid Idempotency-Key header is required.")
        scope = f"projects:{project_id}:mockups"
        key_hash = hashlib.sha256(normalized_key.encode()).hexdigest()
        request_hash = hashlib.sha256(
            json.dumps(
                [project.business, project.design, project.page_layout],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = await self._repository.get_idempotency(
            owner_id=self._owner_id, scope=scope, key_hash=key_hash
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise IdempotencyConflictError(
                    "This idempotency key was already used for a different project draft."
                )
            operation = await self._repository.get_operation(existing.resource_id, self._owner_id)
            if operation is None:
                raise WorkflowNotFoundError("Operation not found")
            return operation_view(operation)

        operation = await self._repository.add_operation(project_id=project_id, kind="mockups")
        await self._repository.enqueue_job(
            "mockups.generate", {"projectId": project_id}, operation_id=operation.id
        )
        await self._repository.add_idempotency(
            owner_id=self._owner_id,
            scope=scope,
            key_hash=key_hash,
            request_hash=request_hash,
            resource_type="operation",
            resource_id=operation.id,
        )
        await self._repository.commit()
        return operation_view(operation)

    async def get_operation(self, operation_id: str) -> OperationView:
        operation = await self._repository.get_operation(operation_id, self._owner_id)
        if operation is None:
            raise WorkflowNotFoundError("Operation not found")
        return operation_view(operation)

    async def list_mockups(self, project_id: str) -> list[MockupView]:
        await self._project(project_id)
        records = list(await self._repository.list_mockups(project_id))
        if not records:
            return []
        latest_generation = records[0].generation
        return [mockup_view(item) for item in records if item.generation == latest_generation]

    async def select_mockup(self, project_id: str, mockup_id: str) -> MockupView:
        project = await self._project(project_id)
        mockup = await self._repository.get_mockup(mockup_id, project_id)
        if mockup is None:
            raise WorkflowNotFoundError("Mockup not found")
        project.selected_mockup_id = mockup.id
        await self._repository.commit()
        return mockup_view(mockup)

    async def get_asset(self, asset_id: str) -> tuple[AssetRecord, bytes]:
        asset = await self._repository.get_asset(asset_id, self._owner_id)
        if asset is None:
            raise WorkflowNotFoundError("Asset not found")
        return asset, await self._asset_store.get(asset.storage_key)

    async def _project(self, project_id: str) -> ProjectRecord:
        project = await self._repository.get_project(project_id, self._owner_id)
        if project is None:
            raise WorkflowNotFoundError("Project not found")
        return project


def asset_view(record: AssetRecord) -> AssetView:
    return AssetView(
        id=record.id,
        kind=record.kind,
        filename=record.filename,
        label=record.label,
        content_type=record.content_type,
        size=record.size,
        preview_url=f"/api/v1/assets/{record.id}/content",
    )


def mockup_view(record: MockupRecord) -> MockupView:
    return MockupView(
        id=record.id,
        generation=record.generation,
        ordinal=record.ordinal,
        label=record.label,
        direction=record.direction,
        preview_url=f"/api/v1/assets/{record.artifact_asset_id}/content",
        created_at=record.created_at,
    )


def operation_view(record: OperationRecord) -> OperationView:
    return OperationView(
        id=record.id,
        project_id=record.project_id,
        kind=record.kind,
        status=record.status,
        result=record.result,
        error_code=record.error_code,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
        completed_at=record.completed_at,
    )


def assets_view(records: Sequence[AssetRecord]) -> list[dict[str, object]]:
    return [asset_view(record).model_dump(by_alias=True) for record in records]


def mockups_view(records: Sequence[MockupRecord]) -> list[dict[str, object]]:
    return [mockup_view(record).model_dump(by_alias=True) for record in records]
