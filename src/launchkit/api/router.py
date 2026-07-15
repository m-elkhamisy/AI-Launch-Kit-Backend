"""Versioned API route registration."""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, Header, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from launchkit.api.auth import (
    AccessCodeRequest,
    AccessCodeResponse,
    AuthTokenResponse,
    VerifyAccessCodeRequest,
    request_access_code,
    verify_access_code,
)
from launchkit.api.catalogs import build_wizard_catalog
from launchkit.api.dependencies import (
    BuildServiceDependency,
    CurrentUserDependency,
    DeploymentServiceDependency,
    ProjectServiceDependency,
    SettingsDependency,
    V0WebhookServiceDependency,
    VercelWebhookServiceDependency,
    WorkflowServiceDependency,
)
from launchkit.api.schemas import HealthResponse, WizardCatalogResponse
from launchkit.builds import BuildCreate, BuildView
from launchkit.builds.sse import stream_build_events
from launchkit.builds.webhooks import WebhookReceipt
from launchkit.deployment import DeploymentCreate, DeploymentView
from launchkit.deployment.webhooks import VercelWebhookReceipt
from launchkit.persistence import Database
from launchkit.projects import ProjectDraft, ProjectPatch, ProjectView
from launchkit.workflows import MockupSelection, MockupView, OperationView

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment, version="1.0.0")


@api_router.get("/ready", response_model=HealthResponse, tags=["system"])
async def readiness(request: Request, settings: SettingsDependency) -> HealthResponse:
    database: Database = request.app.state.database
    async with database.session() as session:
        await session.execute(text("SELECT 1"))
    return HealthResponse(status="ready", environment=settings.environment, version="1.0.0")


@api_router.post(
    "/auth/request-code",
    response_model=AccessCodeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["authentication"],
)
async def request_code(
    request_body: AccessCodeRequest,
    settings: SettingsDependency,
) -> AccessCodeResponse:
    return request_access_code(settings, request_body.email)


@api_router.post(
    "/auth/verify",
    response_model=AuthTokenResponse,
    tags=["authentication"],
)
async def verify_code(
    request_body: VerifyAccessCodeRequest,
    settings: SettingsDependency,
) -> AuthTokenResponse:
    return verify_access_code(settings, request_body.email, request_body.code)


@api_router.get("/catalogs/wizard", response_model=WizardCatalogResponse, tags=["catalogs"])
async def wizard_catalog() -> WizardCatalogResponse:
    return build_wizard_catalog()


@api_router.post(
    "/projects",
    response_model=ProjectView,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(draft: ProjectDraft, service: ProjectServiceDependency) -> ProjectView:
    return await service.create(draft)


@api_router.get("/projects/{project_id}", response_model=ProjectView, tags=["projects"])
async def get_project(project_id: str, service: ProjectServiceDependency) -> ProjectView:
    return await service.get(project_id)


@api_router.patch("/projects/{project_id}", response_model=ProjectView, tags=["projects"])
async def patch_project(
    project_id: str, patch: ProjectPatch, service: ProjectServiceDependency
) -> ProjectView:
    return await service.patch(project_id, patch)


@api_router.post(
    "/projects/{project_id}/profile-extractions",
    response_model=OperationView,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["profiles"],
)
async def start_profile_extraction(
    project_id: str,
    service: WorkflowServiceDependency,
    settings: SettingsDependency,
    profile: Annotated[UploadFile, File()],
) -> OperationView:
    content = await profile.read(settings.upload_max_bytes + 1)
    return await service.start_profile_extraction(
        project_id,
        profile.filename or "",
        profile.content_type or "application/octet-stream",
        content,
    )


@api_router.post(
    "/projects/{project_id}/mockups",
    response_model=OperationView,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["mockups"],
)
async def start_mockups(
    project_id: str,
    service: WorkflowServiceDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> OperationView:
    return await service.start_mockups(project_id, idempotency_key)


@api_router.get("/projects/{project_id}/mockups", response_model=list[MockupView], tags=["mockups"])
async def list_mockups(project_id: str, service: WorkflowServiceDependency) -> list[MockupView]:
    return await service.list_mockups(project_id)


@api_router.put(
    "/projects/{project_id}/selected-mockup", response_model=MockupView, tags=["mockups"]
)
async def select_mockup(
    project_id: str, selection: MockupSelection, service: WorkflowServiceDependency
) -> MockupView:
    return await service.select_mockup(project_id, selection.mockup_id)


@api_router.get("/operations/{operation_id}", response_model=OperationView, tags=["operations"])
async def get_operation(operation_id: str, service: WorkflowServiceDependency) -> OperationView:
    return await service.get_operation(operation_id)


@api_router.get("/assets/{asset_id}/content", tags=["assets"])
async def get_asset_content(asset_id: str, service: WorkflowServiceDependency) -> StreamingResponse:
    asset, content = await service.get_asset(asset_id)
    headers = {
        "Content-Disposition": f'inline; filename="{asset.filename}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=300",
    }
    if asset.content_type.startswith("text/html"):
        headers["Content-Security-Policy"] = (
            "sandbox allow-scripts; default-src 'none'; img-src data: https:; "
            "style-src 'unsafe-inline' https:; script-src 'unsafe-inline' https:; "
            "font-src https: data:"
        )
    return StreamingResponse(BytesIO(content), media_type=asset.content_type, headers=headers)


@api_router.post(
    "/projects/{project_id}/builds",
    response_model=BuildView,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["builds"],
)
async def start_build(
    project_id: str,
    build: BuildCreate,
    service: BuildServiceDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> BuildView:
    return await service.start(project_id, build, idempotency_key)


@api_router.get("/builds/{build_id}", response_model=BuildView, tags=["builds"])
async def get_build(build_id: str, service: BuildServiceDependency) -> BuildView:
    return await service.get(build_id)


@api_router.get("/builds/{build_id}/events", tags=["builds"])
async def get_build_events(
    build_id: str,
    request: Request,
    owner_id: CurrentUserDependency,
    service: BuildServiceDependency,
    settings: SettingsDependency,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    await service.get(build_id)
    try:
        after_sequence = int(last_event_id or 0)
    except ValueError:
        after_sequence = 0
    database: Database = request.app.state.database
    return StreamingResponse(
        stream_build_events(
            database,
            settings,
            build_id=build_id,
            owner_id=owner_id,
            after_sequence=after_sequence,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@api_router.get("/builds/{build_id}/download", tags=["builds"])
async def download_build(build_id: str, service: BuildServiceDependency) -> StreamingResponse:
    content, filename = await service.download(build_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@api_router.post(
    "/builds/{build_id}/deployments",
    response_model=DeploymentView,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["deployments"],
)
async def start_deployment(
    build_id: str,
    deployment: DeploymentCreate,
    service: DeploymentServiceDependency,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> DeploymentView:
    return await service.start(build_id, deployment, idempotency_key)


@api_router.get("/deployments/{deployment_id}", response_model=DeploymentView, tags=["deployments"])
async def get_deployment(
    deployment_id: str, service: DeploymentServiceDependency
) -> DeploymentView:
    return await service.get(deployment_id)


@api_router.post(
    "/webhooks/v0/{token}",
    response_model=WebhookReceipt,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["webhooks"],
)
async def receive_v0_webhook(
    token: str, request: Request, service: V0WebhookServiceDependency
) -> WebhookReceipt:
    return await service.receive(token, await request.body())


@api_router.post(
    "/webhooks/vercel",
    response_model=VercelWebhookReceipt,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["webhooks"],
)
async def receive_vercel_webhook(
    request: Request,
    service: VercelWebhookServiceDependency,
    signature: Annotated[str | None, Header(alias="x-vercel-signature")] = None,
) -> VercelWebhookReceipt:
    return await service.receive(await request.body(), signature)
