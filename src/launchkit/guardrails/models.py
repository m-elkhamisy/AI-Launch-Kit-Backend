"""Guardrail review results."""

from enum import StrEnum

from pydantic import Field

from launchkit.core.models import PythonSourceModel


class GuardrailDecision(StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class GuardrailResult(PythonSourceModel):
    decision: GuardrailDecision
    reason: str = ""
    categories: list[str] = Field(default_factory=list)
