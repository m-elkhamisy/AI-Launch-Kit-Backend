"""Tests for temporary unlimited-generation license checks."""

from types import SimpleNamespace

from launchkit.builds.quota import allows_unlimited_website_generation, extract_license_number
from launchkit.core.config import Settings


def test_settings_parses_comma_separated_licenses() -> None:
    settings = Settings(environment="test", unlimited_test_licenses="07010266, 99999999")
    assert settings.unlimited_test_license_numbers == frozenset({"07010266", "99999999"})


def test_matches_owner_id_directly() -> None:
    licenses = frozenset({"07010266"})
    assert (
        allows_unlimited_website_generation("07010266", None, unlimited_licenses=licenses) is True
    )
    assert allows_unlimited_website_generation("other", None, unlimited_licenses=licenses) is False
    assert (
        allows_unlimited_website_generation("07010266", None, unlimited_licenses=frozenset())
        is False
    )


def test_quota_can_be_disabled_entirely() -> None:
    assert (
        allows_unlimited_website_generation(
            "any-owner",
            None,
            unlimited_licenses=frozenset(),
            quota_disabled=True,
        )
        is True
    )


def test_matches_license_claim_even_without_user_row() -> None:
    assert (
        allows_unlimited_website_generation(
            "cognito-xyz",
            None,
            unlimited_licenses=frozenset({"07010266"}),
            license_number="07010266",
        )
        is True
    )


def test_matches_license_inside_user_profile() -> None:
    user = SimpleNamespace(
        id="cognito-xyz",
        email="a@b.com",
        company_name=None,
        phone=None,
        full_name=None,
        pool=None,
        profile={"account": {"licenseNumber": "07010266"}},
    )
    assert (
        allows_unlimited_website_generation(
            "cognito-xyz",
            user,
            unlimited_licenses=frozenset({"07010266"}),
        )
        is True
    )


def test_extract_license_from_access_token_username() -> None:
    import jwt

    token = jwt.encode(
        {"cognito:username": "07010266", "sub": "abc"},
        key="unused",
        algorithm="HS256",
    )
    assert extract_license_number({}, access_token=token) == "07010266"
