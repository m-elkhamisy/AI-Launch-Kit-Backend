"""Replaceable request dependencies for persistence and temporary authentication."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.api.auth import authenticate_token
from launchkit.assets import AssetBlobStore
from launchkit.builds import BuildService
from launchkit.builds.webhooks import V0WebhookService
from launchkit.core.config import Settings
from launchkit.deployment.service import DeploymentService
from launchkit.deployment.webhooks import VercelWebhookService
from launchkit.persistence import Database, PersistenceRepository
from launchkit.projects import ProjectService
from launchkit.workflows import WorkflowService

bearer_scheme = HTTPBearer(auto_error=False)


def get_request_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_current_user_id(
    settings: Annotated[Settings, Depends(get_request_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    if settings.auth_mode == "testing":
        return settings.testing_user_id
    if credentials is None or credentials.scheme.lower() != "bearer":
        from launchkit.core.exceptions import AuthenticationError

        raise AuthenticationError("Authentication is required.")
    return authenticate_token(settings, credentials.credentials)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
) -> ProjectService:
    return ProjectService(PersistenceRepository(session), owner_id)


def get_workflow_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> WorkflowService:
    store = cast(AssetBlobStore, request.app.state.asset_store)
    return WorkflowService(PersistenceRepository(session), owner_id, settings, store)


def get_build_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> BuildService:
    store = cast(AssetBlobStore, request.app.state.asset_store)
    return BuildService(PersistenceRepository(session), owner_id, settings, store)


def get_v0_webhook_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> V0WebhookService:
    return V0WebhookService(PersistenceRepository(session), settings)


def get_deployment_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> DeploymentService:
    return DeploymentService(PersistenceRepository(session), owner_id, settings)


def get_vercel_webhook_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_request_settings)],
) -> VercelWebhookService:
    return VercelWebhookService(PersistenceRepository(session), settings)


SettingsDependency = Annotated[Settings, Depends(get_request_settings)]
ProjectServiceDependency = Annotated[ProjectService, Depends(get_project_service)]
WorkflowServiceDependency = Annotated[WorkflowService, Depends(get_workflow_service)]
BuildServiceDependency = Annotated[BuildService, Depends(get_build_service)]
V0WebhookServiceDependency = Annotated[V0WebhookService, Depends(get_v0_webhook_service)]
DeploymentServiceDependency = Annotated[DeploymentService, Depends(get_deployment_service)]
VercelWebhookServiceDependency = Annotated[
    VercelWebhookService, Depends(get_vercel_webhook_service)
]
CurrentUserDependency = Annotated[str, Depends(get_current_user_id)]
