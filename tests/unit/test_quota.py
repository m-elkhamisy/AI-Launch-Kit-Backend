"""Tests for generation-quota on/off and IC license extraction (debug)."""

import jwt

from launchkit.builds.quota import extract_license_number
from launchkit.core.config import Settings


def test_generation_quota_disabled_on_local_and_test() -> None:
    assert (
        Settings(environment="local", disable_generation_quota=False, _env_file=None)
        .is_generation_quota_disabled
        is True
    )
    assert (
        Settings(environment="test", disable_generation_quota=False, _env_file=None)
        .is_generation_quota_disabled
        is True
    )


def test_generation_quota_enforced_on_production_unless_flagged() -> None:
    assert (
        Settings(environment="production", disable_generation_quota=False, _env_file=None)
        .is_generation_quota_disabled
        is False
    )
    assert (
        Settings(environment="production", disable_generation_quota=True, _env_file=None)
        .is_generation_quota_disabled
        is True
    )


def test_extract_license_from_access_token_username() -> None:
    token = jwt.encode(
        {"cognito:username": "07010266", "sub": "abc"},
        key="unused",
        algorithm="HS256",
    )
    assert extract_license_number({}, access_token=token) == "07010266"
