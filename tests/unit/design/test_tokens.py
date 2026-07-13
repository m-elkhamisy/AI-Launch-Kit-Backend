import json
from pathlib import Path

from launchkit.design import (
    ColorSwatch,
    DesignPreferences,
    FontChoice,
    FontPairingId,
    PaletteId,
    build_design_tokens_block,
    describe_fonts,
    describe_palette,
    resolve_font_choice,
    resolve_industry_style_direction,
    resolve_palette_colors,
)
from launchkit.intake import OnboardingForm

FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_preset_tokens_match_typescript_fixture() -> None:
    payload = json.loads((FIXTURES / "haseeb_design.json").read_text(encoding="utf-8"))
    design = DesignPreferences.model_validate(payload)

    assert resolve_palette_colors(design) == ColorSwatch(
        primary="#3B6FED",
        secondary="#8FB8F7",
        background="#F5F8FF",
        text="#101B33",
    )
    assert resolve_font_choice(design) == FontChoice(heading="Poppins", body="Inter")
    assert describe_palette(design) == (
        "Modern Blue (primary #3B6FED, secondary #8FB8F7, background #F5F8FF, text #101B33)"
    )
    assert describe_fonts(design) == "Modern Startup — Poppins (headings) + Inter (body)"
    assert build_design_tokens_block(design) == (
        "EXACT DESIGN TOKENS — use these precisely, do not substitute different values:\n"
        "- Primary color: #3B6FED\n"
        "- Secondary color: #8FB8F7\n"
        "- Background color: #F5F8FF\n"
        "- Text color: #101B33\n"
        '- Heading font: "Poppins" (load from Google Fonts)\n'
        '- Body font: "Inter" (load from Google Fonts)'
    )


def test_ai_choice_emits_no_exact_tokens() -> None:
    design = DesignPreferences()

    assert resolve_palette_colors(design) is None
    assert resolve_font_choice(design) is None
    assert describe_palette(design) == "Let the AI choose to fit the brand"
    assert describe_fonts(design) == "Let the AI choose"
    assert build_design_tokens_block(design) == ""


def test_custom_design_choices_are_rendered_exactly() -> None:
    design = DesignPreferences(
        palette_id=PaletteId.CUSTOM,
        custom_palette=ColorSwatch(
            primary="#112233",
            secondary="#445566",
            background="#FFFFFF",
            text="#101010",
        ),
        font_pairing_id=FontPairingId.CUSTOM,
        custom_fonts=FontChoice(heading="Lora", body="Karla"),
    )

    assert describe_palette(design).startswith("Custom palette (primary #112233")
    assert describe_fonts(design) == "Custom pairing — Lora (headings) + Karla (body)"


def test_partial_exact_choices_render_only_the_selected_token_group() -> None:
    palette_only = DesignPreferences(palette_id=PaletteId.MINIMAL)
    fonts_only = DesignPreferences(font_pairing_id=FontPairingId.CORPORATE)

    assert "Primary color" in build_design_tokens_block(palette_only)
    assert "Heading font" not in build_design_tokens_block(palette_only)
    assert "Heading font" in build_design_tokens_block(fonts_only)
    assert "Primary color" not in build_design_tokens_block(fonts_only)


def test_industry_direction_preserves_ordered_case_insensitive_matching() -> None:
    health_clinic = OnboardingForm(industry="HEALTH CLINIC")
    software = OnboardingForm(business_activity="Custom software products")

    assert resolve_industry_style_direction(health_clinic).startswith(
        "INDUSTRY STYLE DIRECTION (health):"
    )
    assert resolve_industry_style_direction(software).startswith(
        "INDUSTRY STYLE DIRECTION (software):"
    )
    assert resolve_industry_style_direction(OnboardingForm(industry="Unknown")) == ""
