"""Deterministic compatibility normalization for company intake."""

import json
from collections.abc import Mapping, Sequence
from typing import Any, Final

from launchkit.intake.models import LegacyCompany, OnboardingField, OnboardingForm

FIELD_MAP: Final[dict[str, tuple[str, ...]]] = {
    "name": ("name", "company_name", "businessName", "business_name"),
    "industry": ("industry", "sector", "category"),
    "tagline": ("tagline", "slogan"),
    "description": ("description", "about", "what_you_do", "summary", "overview"),
    "services": ("services", "offerings", "products", "service_list"),
    "audience": ("audience", "target_audience", "customers", "target"),
    "tone": ("tone", "brand_tone", "voice", "style"),
    "location": ("location", "city", "address"),
    "website": ("website", "url", "site"),
    "contact_email": ("email", "contact_email", "contactEmail"),
    "contact_phone": ("phone", "contact_phone", "phone_number", "contactPhone"),
    "colorway": (
        "colorway",
        "color_way",
        "colors",
        "brand_colors",
        "color_preference",
        "colour",
        "color",
    ),
    "animation_level": ("animation_level", "animations", "motion_level", "animation"),
}

REQUIRED_ONBOARDING_FIELDS: Final[tuple[OnboardingField, ...]] = (
    OnboardingField.COMPANY_NAME,
    OnboardingField.INDUSTRY,
    OnboardingField.BUSINESS_ACTIVITY,
    OnboardingField.TARGET_AUDIENCE,
    OnboardingField.UVP,
)


def flatten_submission(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Merge nested ``raw`` data under curated top-level values."""

    inner = raw.get("raw")
    if isinstance(inner, str):
        try:
            inner = json.loads(inner)
        except (json.JSONDecodeError, TypeError):
            inner = None

    merged: dict[str, Any] = {}
    if isinstance(inner, dict):
        merged.update(inner)
    merged.update({key: value for key, value in raw.items() if key != "raw"})
    return merged


def _first(raw: Mapping[str, Any], candidates: Sequence[str], default: Any = "") -> Any:
    lower = {key.lower(): value for key, value in raw.items() if isinstance(key, str)}
    for candidate in candidates:
        value = lower.get(candidate.lower())
        if value not in (None, "", [], {}):
            return value
    return default


def normalize_company(raw: Mapping[str, Any]) -> LegacyCompany:
    """Return the prompt-ready company shape used by the legacy Python pipeline."""

    flat = flatten_submission(raw)
    services = _first(flat, FIELD_MAP["services"], default=[])
    if isinstance(services, list):
        services = "; ".join(str(service).strip() for service in services if str(service).strip())

    return LegacyCompany(
        name=str(_first(flat, FIELD_MAP["name"], "this company")).strip(),
        industry=str(_first(flat, FIELD_MAP["industry"], "\u2014")).strip(),
        tagline=str(_first(flat, FIELD_MAP["tagline"], "")).strip(),
        description=str(_first(flat, FIELD_MAP["description"], "")).strip(),
        services=str(services or "\u2014").strip(),
        audience=str(_first(flat, FIELD_MAP["audience"], "general customers")).strip(),
        tone=str(_first(flat, FIELD_MAP["tone"], "professional and trustworthy")).strip(),
        location=str(_first(flat, FIELD_MAP["location"], "")).strip(),
        website=str(_first(flat, FIELD_MAP["website"], "")).strip(),
        contact_email=str(_first(flat, FIELD_MAP["contact_email"], "")).strip(),
        contact_phone=str(_first(flat, FIELD_MAP["contact_phone"], "")).strip(),
        colorway=str(_first(flat, FIELD_MAP["colorway"], "")).strip(),
        animation_level=str(_first(flat, FIELD_MAP["animation_level"], "")).strip(),
    )


def missing_required_fields(form: OnboardingForm) -> tuple[OnboardingField, ...]:
    """Return required Haseeb form fields whose values are blank after trimming."""

    values = {
        OnboardingField.COMPANY_NAME: form.company_name,
        OnboardingField.INDUSTRY: form.industry,
        OnboardingField.BUSINESS_ACTIVITY: form.business_activity,
        OnboardingField.TARGET_AUDIENCE: form.target_audience,
        OnboardingField.UVP: form.uvp,
    }
    return tuple(field for field in REQUIRED_ONBOARDING_FIELDS if not values[field].strip())
