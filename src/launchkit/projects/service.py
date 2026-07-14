"""Project application service, independent of HTTP transport."""

from typing import Any

from pydantic import BaseModel

from launchkit.core.exceptions import DomainError
from launchkit.persistence.models import ProjectRecord
from launchkit.persistence.repositories import PersistenceRepository
from launchkit.projects.models import ProjectDraft, ProjectPatch, ProjectView


class ProjectNotFoundError(DomainError):
    """Raised when a project is missing or belongs to another user."""


class ProjectService:
    def __init__(self, repository: PersistenceRepository, owner_id: str) -> None:
        self._repository = repository
        self._owner_id = owner_id

    async def create(self, draft: ProjectDraft) -> ProjectView:
        record = await self._repository.add_project(
            owner_id=self._owner_id,
            business=draft.business.model_dump(by_alias=True),
            design=draft.design.model_dump(by_alias=True),
            page_layout=draft.page_layout.model_dump(by_alias=True),
        )
        await self._repository.commit()
        return self._view(record)

    async def get(self, project_id: str) -> ProjectView:
        return self._view(await self._record(project_id))

    async def patch(self, project_id: str, patch: ProjectPatch) -> ProjectView:
        record = await self._record(project_id)
        business = self._merge(record.business, patch.business)
        design = self._merge(record.design, patch.design)
        page_layout = (
            patch.page_layout.model_dump(by_alias=True)
            if patch.page_layout is not None
            else record.page_layout
        )
        validated = ProjectDraft.model_validate(
            {"business": business, "design": design, "pageLayout": page_layout}
        )
        record.business = validated.business.model_dump(by_alias=True)
        record.design = validated.design.model_dump(by_alias=True)
        record.page_layout = validated.page_layout.model_dump(by_alias=True)
        await self._repository.commit()
        await self._repository.refresh(record)
        return self._view(record)

    async def _record(self, project_id: str) -> ProjectRecord:
        record = await self._repository.get_project(project_id, self._owner_id)
        if record is None:
            raise ProjectNotFoundError("Project not found")
        return record

    @staticmethod
    def _merge(current: dict[str, Any], patch: BaseModel | None) -> dict[str, Any]:
        if patch is None:
            return current
        values = patch.model_dump(by_alias=True, exclude_unset=True)
        return {**current, **values}

    @staticmethod
    def _view(record: ProjectRecord) -> ProjectView:
        return ProjectView.model_validate(
            {
                "id": record.id,
                "status": record.status,
                "business": record.business,
                "design": record.design,
                "pageLayout": record.page_layout,
                "extractedProfileFields": record.extracted_profile_fields,
                "selectedMockupId": record.selected_mockup_id,
                "latestBuildId": record.latest_build_id,
                "latestDeploymentId": record.latest_deployment_id,
                "createdAt": record.created_at,
                "updatedAt": record.updated_at,
            }
        )
