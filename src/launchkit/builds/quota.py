"""Temporary website-generation quota exceptions for internal testing."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import jwt

from launchkit.persistence.models import UserRecord

_LICENSE_PROFILE_KEYS = (
    "licenseNumber",
    "licenceNumber",
    "licenseNo",
    "licenceNo",
    "license",
    "licence",
    "tradeLicence",
    "tradeLicense",
    "username",
    "userName",
    "preferredUsername",
    "preferred_username",
    "loginId",
    "login_id",
)


def extract_license_number(
    profile: Mapping[str, Any] | None = None,
    *,
    access_token: str | None = None,
) -> str | None:
    """Best-effort IC license / login id from /me profile or access-token claims."""

    payload = dict(profile or {})
    for key in _LICENSE_PROFILE_KEYS:
        raw = _nested_get(payload, key)
        if isinstance(raw, (str, int)):
            candidate = _looks_like_license(str(raw))
            if candidate:
                return candidate

    if access_token:
        try:
            claims = jwt.decode(
                access_token,
                options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
            )
        except Exception:
            claims = {}
        if isinstance(claims, Mapping):
            for key in (
                "cognito:username",
                "username",
                "preferred_username",
                "licenseNumber",
                "licenceNumber",
            ):
                raw = claims.get(key)
                if isinstance(raw, (str, int)):
                    candidate = _looks_like_license(str(raw))
                    if candidate:
                        return candidate

    for value in _string_values(payload):
        candidate = _looks_like_license(value)
        if candidate:
            return candidate
    return None


def allows_unlimited_website_generation(
    owner_id: str,
    user: UserRecord | None,
    *,
    unlimited_licenses: frozenset[str],
    license_number: str | None = None,
) -> bool:
    """Return True when this owner may create/generate more than one website."""

    if not unlimited_licenses:
        return False
    for candidate in (license_number, owner_id):
        if _matches_unlimited(candidate, unlimited_licenses):
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
        extract_license_number(user.profile if isinstance(user.profile, dict) else {}),
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
    normalized = value.strip()
    if normalized in unlimited_licenses:
        return True
    # Tolerate missing/extra leading zeros on numeric licenses.
    digits = "".join(ch for ch in normalized if ch.isdigit())
    if not digits:
        return False
    for license_value in unlimited_licenses:
        license_digits = "".join(ch for ch in license_value if ch.isdigit())
        if license_digits and digits.lstrip("0") == license_digits.lstrip("0"):
            return True
    return False


def _looks_like_license(value: str) -> str | None:
    text = value.strip()
    if not text or "@" in text or " " in text:
        return None
    # IC licenses are typically numeric (optionally zero-padded).
    if text.isdigit() and 5 <= len(text) <= 16:
        return text
    return None


def _nested_get(payload: Mapping[str, Any], key: str) -> Any:
    if key in payload:
        return payload[key]
    for value in payload.values():
        if isinstance(value, Mapping):
            found = _nested_get(value, key)
            if found is not None:
                return found
    return None


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
