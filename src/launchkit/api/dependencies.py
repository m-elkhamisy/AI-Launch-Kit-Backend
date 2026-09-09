"""Replaceable request dependencies for persistence and temporary authentication."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.adapters.v0 import V0Adapter
from launchkit.api.auth import API_TOKEN_COOKIE, authenticate_token, read_token_license
from launchkit.assets import AssetBlobStore
from launchkit.builds import BuildService
from launchkit.builds.webhooks import V0WebhookService
from launchkit.core.config import Settings
from launchkit.deployment.service import DeploymentService
from launchkit.deployment.webhooks import VercelWebhookService
from launchkit.generation.models import V0GenerationResult
from launchkit.persistence import Database, PersistenceRepository
from launchkit.projects import ProjectService
from launchkit.workflows import WorkflowService

bearer_scheme = HTTPBearer(auto_error=False)


def get_request_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_current_user_id(
    request: Request,
    settings: Annotated[Settings, Depends(get_request_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str:
    if settings.auth_mode == "testing":
        return settings.testing_user_id
    if credentials is not None and credentials.scheme.lower() == "bearer":
        return authenticate_token(settings, credentials.credentials)
    # IC OAuth logins receive the API JWT in an httpOnly cookie.
    cookie_token = request.cookies.get(API_TOKEN_COOKIE)
    if cookie_token:
        return authenticate_token(settings, cookie_token)
    from launchkit.core.exceptions import AuthenticationError

    raise AuthenticationError("Authentication is required.")


def get_current_license_number(
    request: Request,
    settings: Annotated[Settings, Depends(get_request_settings)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> str | None:
    """Optional IC license claim carried on the Launch Kit API JWT."""

    if settings.auth_mode == "testing":
        return None
    token: str | None = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    else:
        token = request.cookies.get(API_TOKEN_COOKIE)
    if not token:
        return None
    return read_token_license(settings, token)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    owner_id: Annotated[str, Depends(get_current_user_id)],
    settings: Annotated[Settings, Depends(get_request_settings)],
    license_number: Annotated[str | None, Depends(get_current_license_number)],
) -> ProjectService:
    return ProjectService(
        PersistenceRepository(session),
        owner_id,
        settings,
        license_number=license_number,
    )


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
    license_number: Annotated[str | None, Depends(get_current_license_number)],
) -> BuildService:
    store = cast(AssetBlobStore, request.app.state.asset_store)
    v0_key = settings.v0_api_key.get_secret_value() if settings.v0_api_key else ""

    async def v0_status(chat_id: str) -> V0GenerationResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            adapter = V0Adapter(
                client,
                api_key=v0_key,
                base_url=settings.v0_base_url,
                model_id=settings.v0_model,
            )
            return await adapter.get_status(chat_id)

    return BuildService(
        PersistenceRepository(session),
        owner_id,
        settings,
        store,
        v0_status=v0_status if v0_key else None,
        license_number=license_number,
    )


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
