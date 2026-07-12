"""Company intake models from the TypeScript and legacy Python contracts."""

from enum import StrEnum

from launchkit.domain.models.base import DomainModel, PythonSourceModel


class OnboardingField(StrEnum):
    COMPANY_NAME = "companyName"
    INDUSTRY = "industry"
    ACTIVITY_CODE = "activityCode"
    BUSINESS_ACTIVITY = "businessActivity"
    TARGET_AUDIENCE = "targetAudience"
    UVP = "uvp"
    COMPETITORS = "competitors"
    PURPOSE = "purpose"
    STATS = "stats"
    TESTIMONIALS = "testimonials"
    TEAM_BIOS = "teamBios"
    CERTIFICATIONS = "certifications"
    PRODUCTS = "products"
    LOCATION_HOURS = "locationHours"
    SERVICE_AREA = "serviceArea"
    CONTACT = "contact"
    SOCIALS = "socials"
    TONE = "tone"
    AESTHETIC = "aesthetic"
    DESCRIPTION = "description"
    NOTES = "notes"


class OnboardingForm(DomainModel):
    """Rich form used by the consolidated TypeScript generation flow."""

    company_name: str = ""
    industry: str = ""
    activity_code: str = ""
    business_activity: str = ""
    target_audience: str = ""
    uvp: str = ""
    competitors: str = ""
    purpose: str = ""
    stats: str = ""
    testimonials: str = ""
    team_bios: str = ""
    certifications: str = ""
    products: str = ""
    location_hours: str = ""
    service_area: str = ""
    contact: str = ""
    socials: str = ""
    tone: str = ""
    aesthetic: str = ""
    description: str = ""
    notes: str = ""


class OnboardingFormPatch(DomainModel):
    """Partial intake fields returned by profile extraction."""

    company_name: str | None = None
    industry: str | None = None
    activity_code: str | None = None
    business_activity: str | None = None
    target_audience: str | None = None
    uvp: str | None = None
    competitors: str | None = None
    purpose: str | None = None
    stats: str | None = None
    testimonials: str | None = None
    team_bios: str | None = None
    certifications: str | None = None
    products: str | None = None
    location_hours: str | None = None
    service_area: str | None = None
    contact: str | None = None
    socials: str | None = None
    tone: str | None = None
    aesthetic: str | None = None
    description: str | None = None
    notes: str | None = None


class LegacyCompany(PythonSourceModel):
    """Prompt-ready company shape produced by the root storage modules."""

    name: str
    industry: str
    tagline: str
    description: str
    services: str
    audience: str
    tone: str
    location: str
    website: str
    contact_email: str
    contact_phone: str
    colorway: str
    animation_level: str
