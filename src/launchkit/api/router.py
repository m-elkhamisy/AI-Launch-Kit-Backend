"""Versioned API route registration."""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, File, Header, UploadFile, status
from fastapi.responses import StreamingResponse

from launchkit.api.catalogs import build_wizard_catalog
from launchkit.api.dependencies import (
    ProjectServiceDependency,
    SettingsDependency,
    WorkflowServiceDependency,
)
from launchkit.api.schemas import HealthResponse, WizardCatalogResponse
from launchkit.projects import ProjectDraft, ProjectPatch, ProjectView
from launchkit.workflows import MockupSelection, MockupView, OperationView

api_router = APIRouter(prefix="/api/v1")


@api_router.get("/health", response_model=HealthResponse, tags=["system"])
async def health(settings: SettingsDependency) -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.environment, version="1.0.0")


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
