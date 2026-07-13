"""Storage-neutral submission persistence contract."""

from collections.abc import Mapping
from typing import Any, Protocol

from launchkit.intake.models import LegacyCompany
from launchkit.storage.models import RawSubmissionRecord, StoredSubmission


class SubmissionStore(Protocol):
    def save_submission(
        self, raw: Mapping[str, Any], submission_id: str | None = None
    ) -> StoredSubmission:
        """Persist raw and normalized records under one identifier."""

    def get_normalized_submission(self, submission_id: str) -> LegacyCompany:
        """Return the prompt-ready normalized record."""

    def get_raw_submission(self, submission_id: str) -> RawSubmissionRecord:
        """Return the original submitted mapping and identifier."""

    def list_submissions(self) -> list[str]:
        """Return sorted identifiers with normalized records."""
