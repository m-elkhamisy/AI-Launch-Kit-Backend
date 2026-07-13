"""Resolve design choices and render prompt-ready token descriptions."""

from launchkit.design.models import (
    ColorSwatch,
    DesignPreferences,
    FontChoice,
    FontPairingId,
    PaletteId,
)
from launchkit.design.presets import FONT_PRESETS, PALETTE_PRESETS


def resolve_palette_colors(design: DesignPreferences) -> ColorSwatch | None:
    if design.palette_id is PaletteId.CUSTOM:
        return design.custom_palette
    if design.palette_id is PaletteId.AI_CHOICE:
        return None
    return PALETTE_PRESETS[design.palette_id].colors


def resolve_font_choice(design: DesignPreferences) -> FontChoice | None:
    if design.font_pairing_id is FontPairingId.CUSTOM:
        return design.custom_fonts
    if design.font_pairing_id is FontPairingId.AI_CHOICE:
        return None
    return FONT_PRESETS[design.font_pairing_id].choice


def describe_palette(design: DesignPreferences) -> str:
    colors = resolve_palette_colors(design)
    if colors is None:
        return "Let the AI choose to fit the brand"
    if design.palette_id is PaletteId.CUSTOM:
        name = "Custom palette"
    else:
        name = PALETTE_PRESETS[design.palette_id].name
    return (
        f"{name} (primary {colors.primary}, secondary {colors.secondary}, "
        f"background {colors.background}, text {colors.text})"
    )


def describe_fonts(design: DesignPreferences) -> str:
    fonts = resolve_font_choice(design)
    if fonts is None:
        return "Let the AI choose"
    if design.font_pairing_id is FontPairingId.CUSTOM:
        name = "Custom pairing"
    else:
        name = FONT_PRESETS[design.font_pairing_id].category
    return f"{name} — {fonts.heading} (headings) + {fonts.body} (body)"


def build_design_tokens_block(design: DesignPreferences) -> str:
    colors = resolve_palette_colors(design)
    fonts = resolve_font_choice(design)
    if colors is None and fonts is None:
        return ""

    lines = ["EXACT DESIGN TOKENS — use these precisely, do not substitute different values:"]
    if colors is not None:
        lines.extend(
            (
                f"- Primary color: {colors.primary}",
                f"- Secondary color: {colors.secondary}",
                f"- Background color: {colors.background}",
                f"- Text color: {colors.text}",
            )
        )
    if fonts is not None:
        lines.extend(
            (
                f'- Heading font: "{fonts.heading}" (load from Google Fonts)',
                f'- Body font: "{fonts.body}" (load from Google Fonts)',
            )
        )
    return "\n".join(lines)
