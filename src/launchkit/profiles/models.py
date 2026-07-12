"""Profile extraction and image sourcing result models."""

from launchkit.core.models import AliasedModel
from launchkit.intake.models import OnboardingFormPatch


class ExtractedImage(AliasedModel):
    filename: str
    label: str
    data_url: str


class ProfileDesignHints(AliasedModel):
    tagline: str | None = None
    cta: str | None = None


class ProfileExtractionResult(AliasedModel):
    fields: OnboardingFormPatch
    design_hints: ProfileDesignHints
    images: list[ExtractedImage]
    source_filename: str
    warnings: list[str]


class SourcedImage(AliasedModel):
    section: str
    desc: str
    src: str
    alt: str
    credit: str | None = None
