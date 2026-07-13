"""Source-backed color and typography presets."""

from dataclasses import dataclass

from launchkit.design.models import ColorSwatch, FontChoice, FontPairingId, PaletteId


@dataclass(frozen=True, slots=True)
class _PalettePreset:
    name: str
    colors: ColorSwatch


@dataclass(frozen=True, slots=True)
class _FontPreset:
    category: str
    choice: FontChoice


PALETTE_PRESETS: dict[PaletteId, _PalettePreset] = {
    PaletteId.MODERN_BLUE: _PalettePreset(
        "Modern Blue",
        ColorSwatch(primary="#3B6FED", secondary="#8FB8F7", background="#F5F8FF", text="#101B33"),
    ),
    PaletteId.NATURE_GREEN: _PalettePreset(
        "Nature Green",
        ColorSwatch(primary="#359355", secondary="#A6E3B4", background="#F2FBF4", text="#12301C"),
    ),
    PaletteId.ELEGANT_PURPLE: _PalettePreset(
        "Elegant Purple",
        ColorSwatch(primary="#8B5CF6", secondary="#D8CCFB", background="#F8F6FE", text="#241638"),
    ),
    PaletteId.WARM_ORANGE: _PalettePreset(
        "Warm Orange",
        ColorSwatch(primary="#E2803B", secondary="#F3C89A", background="#FDF6EC", text="#4A2A12"),
    ),
    PaletteId.MINIMAL: _PalettePreset(
        "Minimal",
        ColorSwatch(primary="#18181B", secondary="#8A8A93", background="#FFFFFF", text="#18181B"),
    ),
    PaletteId.LUXURY_GOLD: _PalettePreset(
        "Luxury Gold",
        ColorSwatch(primary="#C6A15B", secondary="#E8D08A", background="#17140F", text="#FBF6EA"),
    ),
    PaletteId.SOFT_PINK: _PalettePreset(
        "Soft Pink",
        ColorSwatch(primary="#DB5F94", secondary="#F6C6DD", background="#FFF6FA", text="#5B1D3B"),
    ),
}

FONT_PRESETS: dict[FontPairingId, _FontPreset] = {
    FontPairingId.MODERN_STARTUP: _FontPreset(
        "Modern Startup", FontChoice(heading="Poppins", body="Inter")
    ),
    FontPairingId.ELEGANT_EDITORIAL: _FontPreset(
        "Elegant Editorial", FontChoice(heading="Playfair Display", body="Source Sans 3")
    ),
    FontPairingId.CORPORATE: _FontPreset(
        "Corporate", FontChoice(heading="Montserrat", body="Open Sans")
    ),
    FontPairingId.PROFESSIONAL_BLOG: _FontPreset(
        "Professional Blog", FontChoice(heading="Merriweather", body="Lato")
    ),
    FontPairingId.TECH_SAAS: _FontPreset(
        "Tech & SaaS", FontChoice(heading="Space Grotesk", body="Inter")
    ),
    FontPairingId.LUXURY_BRAND: _FontPreset(
        "Luxury Brand", FontChoice(heading="DM Serif Display", body="Manrope")
    ),
    FontPairingId.CREATIVE_STUDIO: _FontPreset(
        "Creative Studio", FontChoice(heading="Bebas Neue", body="Nunito Sans")
    ),
}
