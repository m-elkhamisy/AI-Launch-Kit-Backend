"""Intake validation and normalization."""

from launchkit.application.intake.normalization import (
    flatten_submission,
    missing_required_fields,
    normalize_company,
)

__all__ = ["flatten_submission", "missing_required_fields", "normalize_company"]
