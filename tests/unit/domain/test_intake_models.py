import pytest
from pydantic import ValidationError

from launchkit.domain.models import LegacyCompany, OnboardingForm, OnboardingFormPatch


def test_onboarding_form_preserves_camel_case_contract() -> None:
    form = OnboardingForm.model_validate({"companyName": "Acme", "targetAudience": "Founders"})

    assert form.company_name == "Acme"
    assert form.model_dump(by_alias=True)["targetAudience"] == "Founders"
    assert form.activity_code == ""


def test_onboarding_patch_omits_absent_fields() -> None:
    patch = OnboardingFormPatch.model_validate({"companyName": "Acme"})

    assert patch.model_dump(by_alias=True, exclude_none=True) == {"companyName": "Acme"}


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        OnboardingForm.model_validate({"companyName": "Acme", "unknown": "value"})


def test_legacy_company_keeps_python_field_names() -> None:
    company = LegacyCompany(
        name="Acme",
        industry="Tech",
        tagline="",
        description="Tools",
        services="Automation",
        audience="Teams",
        tone="Direct",
        location="Dubai",
        website="",
        contact_email="hello@example.com",
        contact_phone="",
        colorway="blue",
        animation_level="subtle",
    )

    assert company.model_dump()["contact_email"] == "hello@example.com"
