"""Transport response models that do not belong to one domain capability."""

from launchkit.core.models import AliasedModel
from launchkit.design.models import ColorSwatch, FontChoice


class HealthResponse(AliasedModel):
    status: str
    environment: str
    version: str


class ChoiceResponse(AliasedModel):
    id: str
    label: str
    description: str = ""


class PaletteResponse(AliasedModel):
    id: str
    label: str
    colors: ColorSwatch | None = None


class FontPairingResponse(AliasedModel):
    id: str
    label: str
    fonts: FontChoice | None = None


class SectionTemplateResponse(AliasedModel):
    id: str
    label: str
    locked: bool


class PageTemplateResponse(AliasedModel):
    id: str
    label: str
    slug: str
    section_template_ids: list[str]
    selected_by_default: bool


class WizardCatalogResponse(AliasedModel):
    business_categories: list[ChoiceResponse]
    design_moods: list[ChoiceResponse]
    animation_levels: list[ChoiceResponse]
    theme_modes: list[ChoiceResponse]
    palettes: list[PaletteResponse]
    font_pairings: list[FontPairingResponse]
    page_templates: list[PageTemplateResponse]
    section_templates: list[SectionTemplateResponse]
