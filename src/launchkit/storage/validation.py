"""Submission identifier validation shared by storage adapters."""

import re

from launchkit.core.exceptions import DomainError

VALID_ID = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_submission_id(submission_id: str) -> str:
    if not submission_id or not VALID_ID.fullmatch(submission_id):
        raise DomainError(
            "Submission id may contain only letters, numbers, underscores, and hyphens"
        )
    return submission_id
