import pytest
from pydantic import ValidationError

from launchkit.domain.models import (
    AnimationOption,
    ColorSwatch,
    DesignPreferences,
    FontChoice,
    FontPairingId,
    ImageSource,
    PaletteId,
    StyleOption,
)


def test_design_defaults_match_typescript() -> None:
    design = DesignPreferences()

    assert design.style is StyleOption.MODERN
    assert design.animation is AnimationOption.MEDIUM
    assert design.image_source is ImageSource.PLACEHOLDER
    assert design.model_dump(by_alias=True)["paletteId"] == "ai-choice"


def test_custom_palette_and_fonts_serialize_with_aliases() -> None:
    design = DesignPreferences(
        palette_id=PaletteId.CUSTOM,
        custom_palette=ColorSwatch(
            primary="#112233",
            secondary="#445566",
            background="#FFFFFF",
            text="#111111",
        ),
        font_pairing_id=FontPairingId.CUSTOM,
        custom_fonts=FontChoice(heading="Poppins", body="Inter"),
    )

    payload = design.model_dump(by_alias=True, mode="json")
    assert payload["customPalette"]["primary"] == "#112233"
    assert payload["customFonts"]["body"] == "Inter"


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        ({"paletteId": "custom"}, "customPalette"),
        (
            {
                "customPalette": {
                    "primary": "#000000",
                    "secondary": "#000000",
                    "background": "#FFFFFF",
                    "text": "#000000",
                }
            },
            "customPalette",
        ),
        ({"fontPairingId": "custom"}, "customFonts"),
    ],
)
def test_custom_choice_pairs_are_consistent(
    payload: dict[str, object], expected_message: str
) -> None:
    with pytest.raises(ValidationError, match=expected_message):
        DesignPreferences.model_validate(payload)


def test_invalid_enum_and_hex_are_rejected() -> None:
    with pytest.raises(ValidationError):
        DesignPreferences.model_validate({"style": "unknown"})
    with pytest.raises(ValidationError):
        ColorSwatch(primary="blue", secondary="#000000", background="#FFFFFF", text="#000000")
