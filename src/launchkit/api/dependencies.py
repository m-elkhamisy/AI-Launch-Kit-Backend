"""Replaceable request dependencies for persistence and temporary authentication."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.core.config import Settings
from launchkit.persistence import Database, PersistenceRepository
from launchkit.projects import ProjectService


def get_request_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_current_user_id(settings: Annotated[Settings, Depends(get_request_settings)]) -> str:
    return settings.testing_user_id


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> ProjectService:
    return ProjectService(PersistenceRepository(session), owner_id)


SettingsDependency = Annotated[Settings, Depends(get_request_settings)]
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]
