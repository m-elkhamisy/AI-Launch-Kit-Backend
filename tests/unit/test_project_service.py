"""Project service: one website journey per owner."""

import asyncio
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from launchkit.builds.service import GenerationQuotaExceededError
from launchkit.core.config import Settings
from launchkit.persistence.models import ProjectRecord
from launchkit.projects.models import ProjectDraft
from launchkit.projects.service import ProjectService


def quota_enforced_settings() -> Settings:
    """Pin the quota knobs: ``load_dotenv_file`` leaks a developer's .env into os.environ."""

    return Settings(
        # Use staging so local/test auto-bypass does not skip the quota under test.
        environment="staging",
        disable_generation_quota=False,
        _env_file=None,
    )


class RepositoryStub:
    def __init__(self) -> None:
        self.projects: list[ProjectRecord] = []
        self.owner_build_count = 0
        self.commits = 0
        self.user: Any | None = None

    async def get_user(self, user_id: str) -> Any | None:
        del user_id
        return self.user

    async def count_owner_website_builds(self, owner_id: str) -> int:
        del owner_id
        return self.owner_build_count

    async def list_projects(self, owner_id: str) -> list[ProjectRecord]:
        return [project for project in self.projects if project.owner_id == owner_id]

    async def add_project(
        self,
        *,
        owner_id: str,
        business: dict[str, Any],
        design: dict[str, Any],
        page_layout: dict[str, Any],
    ) -> ProjectRecord:
        now = datetime.now(UTC)
        record = ProjectRecord(
            id=f"prj_{len(self.projects) + 1}",
            owner_id=owner_id,
            status="draft",
            business=business,
            design=design,
            page_layout=page_layout,
            extracted_profile_fields={},
            created_at=now,
            updated_at=now,
        )
        self.projects.append(record)
        return record

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, record: ProjectRecord) -> None:
        del record

    async def list_assets(self, project_id: str) -> list[Any]:
        del project_id
        return []

    async def delete_asset(self, asset: Any) -> None:
        del asset

    async def list_mockups(self, project_id: str) -> list[Any]:
        del project_id
        return []


def test_create_reuses_project_slot_but_resets_the_draft() -> None:
    repository = RepositoryStub()
    service = ProjectService(cast(Any, repository), "owner-1", quota_enforced_settings())
    draft = ProjectDraft()
    first = asyncio.run(service.create(draft))
    repository.projects[0].business = {**repository.projects[0].business, "companyName": "Old Co"}
    repository.projects[0].extracted_profile_fields = {"description": "stale"}
    second = asyncio.run(service.create(draft))
    assert first.id == second.id
    assert len(repository.projects) == 1
    assert second.business.company_name == ""
    assert second.extracted_profile_fields == {}


def test_create_blocks_after_website_generation() -> None:
    repository = RepositoryStub()
    repository.owner_build_count = 1
    service = ProjectService(cast(Any, repository), "owner-1", quota_enforced_settings())
    with pytest.raises(GenerationQuotaExceededError, match="need more credits"):
        asyncio.run(service.create(ProjectDraft()))


def test_create_allows_extra_projects_when_quota_disabled() -> None:
    repository = RepositoryStub()
    repository.owner_build_count = 1
    service = ProjectService(
        cast(Any, repository),
        "owner-1",
        Settings(environment="staging", disable_generation_quota=True, _env_file=None),
    )
    first = asyncio.run(service.create(ProjectDraft()))
    second = asyncio.run(service.create(ProjectDraft()))
    assert first.id != second.id
    assert len(repository.projects) == 2
