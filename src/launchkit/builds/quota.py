"""Temporary website-generation quota exceptions for internal testing."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from launchkit.persistence.models import UserRecord


def allows_unlimited_website_generation(
    owner_id: str,
    user: UserRecord | None,
    *,
    unlimited_licenses: frozenset[str],
) -> bool:
    """Return True when this owner may create/generate more than one website."""

    if not unlimited_licenses:
        return False
    if _matches_unlimited(owner_id, unlimited_licenses):
        return True
    if user is None:
        return False
    for candidate in (
        user.id,
        user.email,
        user.company_name,
        user.phone,
        user.full_name,
        user.pool,
    ):
        if _matches_unlimited(candidate, unlimited_licenses):
            return True
    return any(
        _matches_unlimited(value, unlimited_licenses)
        for value in _string_values(user.profile or {})
    )


def _matches_unlimited(value: str | None, unlimited_licenses: frozenset[str]) -> bool:
    if value is None:
        return False
    return value.strip() in unlimited_licenses


def _string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _string_values(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _string_values(nested)
