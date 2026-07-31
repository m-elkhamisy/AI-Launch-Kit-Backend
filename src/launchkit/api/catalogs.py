"""Build the public wizard catalog from authoritative domain presets."""

from launchkit.api.schemas import (
    ChoiceResponse,
    FontPairingResponse,
    PageTemplateResponse,
    PaletteResponse,
    SectionTemplateResponse,
    WizardCatalogResponse,
)
from launchkit.design.models import FontPairingId, PaletteId
from launchkit.design.presets import FONT_PRESETS, PALETTE_PRESETS
from launchkit.projects.catalogs import (
    ANIMATION_LEVELS,
    BUSINESS_CATEGORIES,
    DESIGN_MOODS,
    PAGE_TEMPLATES,
    SECTION_TEMPLATES,
    THEME_MODES,
    Choice,
)


def choices(items: tuple[Choice, ...]) -> list[ChoiceResponse]:
    return [
        ChoiceResponse(id=item.id, label=item.label, description=item.description) for item in items
    ]


def build_wizard_catalog() -> WizardCatalogResponse:
    palettes = [
        PaletteResponse(id=item.value, label=preset.name, colors=preset.colors)
        for item, preset in PALETTE_PRESETS.items()
    ]
    palettes.extend(
        (
            PaletteResponse(id=PaletteId.AI_CHOICE.value, label="Let AI choose"),
            PaletteResponse(id=PaletteId.CUSTOM.value, label="Custom palette"),
        )
    )
    fonts = [
        FontPairingResponse(id=item.value, label=preset.category, fonts=preset.choice)
        for item, preset in FONT_PRESETS.items()
    ]
    fonts.extend(
        (
            FontPairingResponse(id=FontPairingId.AI_CHOICE.value, label="Let AI choose"),
            FontPairingResponse(id=FontPairingId.CUSTOM.value, label="Custom pairing"),
        )
    )
    return WizardCatalogResponse(
        business_categories=choices(BUSINESS_CATEGORIES),
        design_moods=choices(DESIGN_MOODS),
        animation_levels=choices(ANIMATION_LEVELS),
        theme_modes=choices(THEME_MODES),
        palettes=palettes,
        font_pairings=fonts,
        page_templates=[
            PageTemplateResponse(
                id=item.id,
                label=item.label,
                slug=item.slug,
                section_template_ids=list(item.sections),
                selected_by_default=item.selected_by_default,
            )
            for item in PAGE_TEMPLATES
        ],
        section_templates=[
            SectionTemplateResponse(id=item.id, label=item.label, locked=item.locked)
            for item in SECTION_TEMPLATES
        ],
    )
