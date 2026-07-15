"""Deployment API, provider, and ownership-transfer models."""

from datetime import datetime
from enum import StrEnum

from launchkit.core.models import AliasedModel


class DeploymentStatus(StrEnum):
    QUEUED = "queued"
    CREATING = "creating"
    BUILDING = "building"
    READY_TO_CLAIM = "ready_to_claim"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DeploymentCreate(AliasedModel):
    provider: str = "vercel"


class DeploymentView(AliasedModel):
    id: str
    build_id: str
    status: DeploymentStatus
    live_url: str | None = None
    claim_url: str | None = None
    claim_expires_at: datetime | None = None
    message: str
    retry_after_seconds: int | None = None
    created_at: datetime
    updated_at: datetime


class DeploymentResult(AliasedModel):
    status: DeploymentStatus = DeploymentStatus.READY_TO_CLAIM
    chat_id: str
    project_id: str
    deployment_id: str | None
    live_url: str | None
    claim_url: str
    claim_expires: str = "24 hours"
    note: str


class DeploymentFile(AliasedModel):
    file: str
    data: str
    encoding: str | None = None


class VercelDeployment(AliasedModel):
    project_id: str
    deployment_id: str | None
    url: str | None
