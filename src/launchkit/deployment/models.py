"""Deployment and ownership-transfer results."""

from enum import StrEnum

from launchkit.core.models import AliasedModel


class DeploymentStatus(StrEnum):
    READY_TO_CLAIM = "ready_to_claim"


class DeploymentResult(AliasedModel):
    status: DeploymentStatus = DeploymentStatus.READY_TO_CLAIM
    chat_id: str
    project_id: str
    deployment_id: str | None
    live_url: str | None
    claim_url: str
    claim_expires: str = "24 hours"
    note: str
