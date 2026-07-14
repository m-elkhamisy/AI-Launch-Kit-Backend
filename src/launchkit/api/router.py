"""Versioned API route registration."""

from fastapi import APIRouter, status

from launchkit.api.catalogs import build_wizard_catalog
from launchkit.api.dependencies import ProjectServiceDependency, SettingsDependency
from launchkit.api.schemas import HealthResponse, WizardCatalogResponse
from launchkit.projects import ProjectDraft, ProjectPatch, ProjectView

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
