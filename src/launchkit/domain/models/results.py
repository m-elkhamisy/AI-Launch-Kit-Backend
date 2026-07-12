"""Guardrail, persistence, and deployment result models."""

from enum import StrEnum
from typing import Any

from pydantic import Field

from launchkit.domain.models.base import DomainModel, PythonSourceModel
from launchkit.domain.models.intake import LegacyCompany


class GuardrailDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class GuardrailResult(PythonSourceModel):
    decision: GuardrailDecision
    reason: str = ""
    categories: list[str] = Field(default_factory=list)


class StorageMetadata(PythonSourceModel):
    id: str


class StoredSubmission(PythonSourceModel):
    id: str
    raw: dict[str, Any]
    normalized: LegacyCompany


class DeploymentStatus(StrEnum):
    READY_TO_CLAIM = "ready_to_claim"


class DeploymentResult(DomainModel):
    status: DeploymentStatus = DeploymentStatus.READY_TO_CLAIM
    chat_id: str
    project_id: str
    deployment_id: str | None
    live_url: str | None
    claim_url: str
    claim_expires: str = "24 hours"
    note: str
