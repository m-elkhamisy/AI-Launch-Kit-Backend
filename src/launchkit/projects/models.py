"""Strict project draft models and cross-step validation."""

from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from launchkit.core.models import AliasedModel
from launchkit.design.models import (
    ColorSwatch,
    DesignPreferences,
    FontChoice,
    FontPairingId,
    ImageSource,
    PaletteId,
)
from launchkit.intake.models import OnboardingForm, OnboardingFormPatch
from launchkit.projects.catalogs import (
    ANIMATION_IDS,
    ANIMATION_MAP,
    BUSINESS_CATEGORY_IDS,
    FONT_IDS,
    MOOD_IDS,
    MOOD_STYLE_MAP,
    PAGE_BY_ID,
    PALETTE_IDS,
    SECTION_BY_ID,
    THEME_IDS,
    THEME_MAP,
)


def require_known(value: str, known: set[str], field: str) -> str:
    if value not in known:
        raise ValueError(f"unknown {field}: {value}")
    return value


class BusinessDraft(OnboardingForm):
    category_id: str = "tech-saas"

    @model_validator(mode="after")
    def validate_category(self) -> Self:
        require_known(self.category_id, BUSINESS_CATEGORY_IDS, "business category ID")
        return self


class BusinessPatch(OnboardingFormPatch):
    category_id: str | None = None


class DesignDraft(AliasedModel):
    tagline: str = ""
    cta: str = ""
    mood_id: str = "dark-modern"
    animation_id: str = "balanced"
    theme_id: str = "light"
    image_source: ImageSource = ImageSource.PLACEHOLDER
    palette_id: str = "modern-blue"
    custom_palette: ColorSwatch | None = None
    font_pairing_id: str = "modern-startup"
    custom_fonts: FontChoice | None = None

    @model_validator(mode="after")
    def validate_choices(self) -> Self:
        require_known(self.mood_id, MOOD_IDS, "design mood ID")
        require_known(self.animation_id, ANIMATION_IDS, "animation ID")
        require_known(self.theme_id, THEME_IDS, "theme ID")
        require_known(self.palette_id, PALETTE_IDS, "palette ID")
        require_known(self.font_pairing_id, FONT_IDS, "font pairing ID")
        if (self.palette_id == "custom") != (self.custom_palette is not None):
            raise ValueError("customPalette is required only for the custom palette")
        if (self.font_pairing_id == "custom") != (self.custom_fonts is not None):
            raise ValueError("customFonts is required only for custom fonts")
        return self

    def to_preferences(self) -> DesignPreferences:
        return DesignPreferences(
            tagline=self.tagline,
            cta=self.cta,
            style=MOOD_STYLE_MAP[self.mood_id],
            animation=ANIMATION_MAP[self.animation_id],
            theme=THEME_MAP[self.theme_id],
            image_source=self.image_source,
            palette_id=PaletteId(self.palette_id),
            custom_palette=self.custom_palette,
            font_pairing_id=FontPairingId(self.font_pairing_id),
            custom_fonts=self.custom_fonts,
        )


class DesignPatch(AliasedModel):
    tagline: str | None = None
    cta: str | None = None
    mood_id: str | None = None
    animation_id: str | None = None
    theme_id: str | None = None
    image_source: ImageSource | None = None
    palette_id: str | None = None
    custom_palette: ColorSwatch | None = None
    font_pairing_id: str | None = None
    custom_fonts: FontChoice | None = None


class SectionDraft(AliasedModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9:_-]+$")
    template_id: str
    name: str = Field(min_length=1, max_length=80)
    locked: bool = False

    @model_validator(mode="after")
    def validate_template(self) -> Self:
        template = SECTION_BY_ID.get(self.template_id)
        if template is None:
            raise ValueError(f"unknown section template ID: {self.template_id}")
        if self.locked != template.locked:
            raise ValueError(f"locked state for {self.template_id} must be {template.locked}")
        return self


class PageDraft(AliasedModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9:_-]+$")
    template_id: str
    name: str = Field(min_length=1, max_length=80)
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    sections: list[SectionDraft] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_page(self) -> Self:
        if self.template_id not in PAGE_BY_ID:
            raise ValueError(f"unknown page template ID: {self.template_id}")
        if len({section.id for section in self.sections}) != len(self.sections):
            raise ValueError("section IDs must be unique within a page")
        if self.sections[0].template_id != "navigation" or not self.sections[0].locked:
            raise ValueError("locked navigation must be the first section")
        if self.sections[-1].template_id != "footer" or not self.sections[-1].locked:
            raise ValueError("locked footer must be the last section")
        if any(section.locked for section in self.sections[1:-1]):
            raise ValueError("only navigation and footer may be locked")
        if not any(not section.locked for section in self.sections):
            raise ValueError("every selected page must contain an editable content section")
        return self


class PageLayout(AliasedModel):
    pages: list[PageDraft] = Field(min_length=1, max_length=6)

    @model_validator(mode="after")
    def validate_layout(self) -> Self:
        if len({page.id for page in self.pages}) != len(self.pages):
            raise ValueError("page IDs must be unique")
        if len({page.template_id for page in self.pages}) != len(self.pages):
            raise ValueError("page template IDs must be unique")
        if len({page.slug for page in self.pages}) != len(self.pages):
            raise ValueError("page slugs must be unique")
        editable_count = sum(not section.locked for page in self.pages for section in page.sections)
        if editable_count > 24:
            raise ValueError("a project may contain at most 24 editable content sections")
        return self


def default_page_layout() -> PageLayout:
    pages: list[PageDraft] = []
    for page_id in ("home", "about", "contact"):
        template = PAGE_BY_ID[page_id]
        sections = [
            SectionDraft(
                id=f"{template.id}:{section_id}:{index}",
                template_id=section_id,
                name=SECTION_BY_ID[section_id].label,
                locked=SECTION_BY_ID[section_id].locked,
            )
            for index, section_id in enumerate(template.sections)
        ]
        pages.append(
            PageDraft(
                id=f"page:{template.id}",
                template_id=template.id,
                name=template.label,
                slug=template.slug,
                sections=sections,
            )
        )
    return PageLayout(pages=pages)


class ProjectDraft(AliasedModel):
    business: BusinessDraft = Field(default_factory=BusinessDraft)
    design: DesignDraft = Field(default_factory=DesignDraft)
    page_layout: PageLayout = Field(default_factory=default_page_layout)


class ProjectPatch(AliasedModel):
    business: BusinessPatch | None = None
    design: DesignPatch | None = None
    page_layout: PageLayout | None = None


class ProjectView(ProjectDraft):
    id: str
    status: str
    extracted_profile_fields: dict[str, str] = Field(default_factory=dict)
    uploaded_assets: list[dict[str, object]] = Field(default_factory=list)
    mockups: list[dict[str, object]] = Field(default_factory=list)
    selected_mockup_id: str | None = None
    latest_build_id: str | None = None
    latest_deployment_id: str | None = None
    created_at: datetime
    updated_at: datetime
