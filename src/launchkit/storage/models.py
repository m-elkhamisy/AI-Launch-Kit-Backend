"""Storage-neutral submission records."""

from typing import Any

from launchkit.core.models import PythonSourceModel
from launchkit.intake.models import LegacyCompany


class StorageMetadata(PythonSourceModel):
    id: str


class StoredSubmission(PythonSourceModel):
    id: str
    raw: dict[str, Any]
    normalized: LegacyCompany
