"""Injected-client S3 implementation of submission persistence."""

import json
import uuid
from collections.abc import Iterable, Mapping
from typing import Any, Protocol, cast

from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from launchkit.core.exceptions import ApplicationError
from launchkit.intake.models import LegacyCompany
from launchkit.intake.normalization import normalize_company
from launchkit.storage.local import SubmissionNotFound
from launchkit.storage.models import RawSubmissionRecord, StoredSubmission
from launchkit.storage.validation import validate_submission_id


class S3Paginator(Protocol):
    def paginate(self, **kwargs: Any) -> Iterable[Mapping[str, Any]]:
        """Return pages from an S3 list operation."""


class S3Client(Protocol):
    def put_object(self, **kwargs: Any) -> object:
        """Put one object."""

    def get_object(self, **kwargs: Any) -> Mapping[str, Any]:
        """Get one object."""

    def get_paginator(self, operation_name: str) -> S3Paginator:
        """Return an S3 paginator."""


class ReadableBody(Protocol):
    def read(self) -> bytes:
        """Read an SDK response body."""


class S3SubmissionStore:
    """Persist legacy-compatible raw and normalized records in S3."""

    def __init__(self, client: S3Client, *, bucket: str, prefix: str = "submissions/") -> None:
        if not bucket:
            raise ApplicationError("S3 bucket is required")
        self._client = client
        self._bucket = bucket
        base = prefix.strip("/")
        self._raw_prefix = f"{base}/raw/" if base else "raw/"
        self._normalized_prefix = f"{base}/normalized/" if base else "normalized/"

    def save_submission(
        self, raw: Mapping[str, Any], submission_id: str | None = None
    ) -> StoredSubmission:
        identifier = validate_submission_id(submission_id or uuid.uuid4().hex)
        raw_data = dict(raw)
        normalized = normalize_company(raw_data)
        self._put(f"{self._raw_prefix}{identifier}.json", {"id": identifier, "data": raw_data})
        self._put(
            f"{self._normalized_prefix}{identifier}.json",
            {"id": identifier, **normalized.model_dump()},
        )
        return StoredSubmission(id=identifier, raw=raw_data, normalized=normalized)

    def get_normalized_submission(self, submission_id: str) -> LegacyCompany:
        identifier = validate_submission_id(submission_id)
        payload = self._get(f"{self._normalized_prefix}{identifier}.json")
        payload.pop("id", None)
        return LegacyCompany.model_validate(payload)

    def get_raw_submission(self, submission_id: str) -> RawSubmissionRecord:
        identifier = validate_submission_id(submission_id)
        return RawSubmissionRecord.model_validate(self._get(f"{self._raw_prefix}{identifier}.json"))

    def list_submissions(self) -> list[str]:
        identifiers: list[str] = []
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=self._normalized_prefix):
            contents = page.get("Contents", [])
            if not isinstance(contents, list):
                continue
            for item in contents:
                key = item.get("Key") if isinstance(item, Mapping) else None
                if isinstance(key, str) and key.endswith(".json"):
                    identifiers.append(key[len(self._normalized_prefix) : -len(".json")])
        return sorted(identifiers)

    def _put(self, key: str, payload: Mapping[str, Any]) -> None:
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False, indent=2).encode(),
            ContentType="application/json",
        )

    def _get(self, key: str) -> dict[str, Any]:
        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise SubmissionNotFound(key) from exc
            raise
        body = response.get("Body")
        payload = json.loads(cast(ReadableBody, body).read()) if hasattr(body, "read") else None
        if not isinstance(payload, dict):
            raise ApplicationError(f"Stored S3 submission is not a JSON object: {key}")
        return payload
