"""Profile extraction and image sourcing result models."""

from launchkit.domain.models.base import DomainModel
from launchkit.domain.models.intake import OnboardingFormPatch


class ExtractedImage(DomainModel):
    filename: str
    label: str
    data_url: str


class ProfileDesignHints(DomainModel):
    tagline: str | None = None
    cta: str | None = None


class ProfileExtractionResult(DomainModel):
    fields: OnboardingFormPatch
    design_hints: ProfileDesignHints
    images: list[ExtractedImage]
    source_filename: str
    warnings: list[str]


class SourcedImage(DomainModel):
    section: str
    desc: str
    src: str
    alt: str
    credit: str | None = None
