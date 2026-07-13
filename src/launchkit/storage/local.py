"""Local JSON-file implementation of submission persistence."""

import json
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from launchkit.core.exceptions import ApplicationError
from launchkit.intake.models import LegacyCompany
from launchkit.intake.normalization import normalize_company
from launchkit.storage.models import RawSubmissionRecord, StoredSubmission
from launchkit.storage.validation import validate_submission_id


class SubmissionNotFound(ApplicationError):
    """Raised when no stored submission matches an identifier."""


class LocalSubmissionStore:
    """Persist raw and normalized submissions using the legacy two-file layout."""

    def __init__(self, base_dir: Path) -> None:
        self._raw_dir = base_dir / "submissions" / "raw"
        self._normalized_dir = base_dir / "submissions" / "normalized"
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._normalized_dir.mkdir(parents=True, exist_ok=True)

    def save_submission(
        self, raw: Mapping[str, Any], submission_id: str | None = None
    ) -> StoredSubmission:
        identifier = validate_submission_id(submission_id or uuid.uuid4().hex)
        raw_data = dict(raw)
        normalized = normalize_company(raw_data)
        self._write(self._raw_dir / f"{identifier}.json", {"id": identifier, "data": raw_data})
        self._write(
            self._normalized_dir / f"{identifier}.json",
            {"id": identifier, **normalized.model_dump()},
        )
        return StoredSubmission(id=identifier, raw=raw_data, normalized=normalized)

    def get_normalized_submission(self, submission_id: str) -> LegacyCompany:
        identifier = validate_submission_id(submission_id)
        payload = self._read(self._normalized_dir / f"{identifier}.json")
        payload.pop("id", None)
        return LegacyCompany.model_validate(payload)

    def get_raw_submission(self, submission_id: str) -> RawSubmissionRecord:
        identifier = validate_submission_id(submission_id)
        return RawSubmissionRecord.model_validate(self._read(self._raw_dir / f"{identifier}.json"))

    def list_submissions(self) -> list[str]:
        return sorted(path.stem for path in self._normalized_dir.glob("*.json"))

    @staticmethod
    def _write(path: Path, payload: Mapping[str, Any]) -> None:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise SubmissionNotFound(path.stem)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ApplicationError(f"Stored submission is not a JSON object: {path.name}")
        return payload
