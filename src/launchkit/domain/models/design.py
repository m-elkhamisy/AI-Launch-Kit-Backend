"""Site-wide design preference models and source-defined choices."""

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from launchkit.domain.models.base import DomainModel


class StyleOption(StrEnum):
    LUXURY = "Luxury / elegant"
    MODERN = "Modern / minimal"
    BOLD = "Bold / playful"
    CORPORATE = "Corporate / professional"
    WARM = "Warm / organic"
    DARK_TECH = "Dark / premium tech"


class AnimationOption(StrEnum):
    NONE = "None (static)"
    SUBTLE = "Subtle (gentle fades on scroll)"
    MEDIUM = "Medium (hover effects + scroll reveals)"
    HIGH = "High (rich motion everywhere)"


class ThemeOption(StrEnum):
    LIGHT = "Light mode"
    DARK = "Dark mode"
    TOGGLE = "Light + dark (theme toggle)"


class ImageSource(StrEnum):
    PEXELS = "pexels"
    AI = "ai"
    UPLOADED = "uploaded"
    PLACEHOLDER = "placeholder"


class PaletteId(StrEnum):
    MODERN_BLUE = "modern-blue"
    NATURE_GREEN = "nature-green"
    ELEGANT_PURPLE = "elegant-purple"
    WARM_ORANGE = "warm-orange"
    MINIMAL = "minimal"
    LUXURY_GOLD = "luxury-gold"
    SOFT_PINK = "soft-pink"
    AI_CHOICE = "ai-choice"
    CUSTOM = "custom"


class FontPairingId(StrEnum):
    MODERN_STARTUP = "modern-startup"
    ELEGANT_EDITORIAL = "elegant-editorial"
    CORPORATE = "corporate"
    PROFESSIONAL_BLOG = "professional-blog"
    TECH_SAAS = "tech-saas"
    LUXURY_BRAND = "luxury-brand"
    CREATIVE_STUDIO = "creative-studio"
    AI_CHOICE = "ai-choice"
    CUSTOM = "custom"


class ColorSwatch(DomainModel):
    primary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    background: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    text: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class FontChoice(DomainModel):
    heading: str
    body: str


class DesignPreferences(DomainModel):
    """Look-and-feel choices applied across every generation provider."""

    tagline: str = ""
    style: StyleOption = StyleOption.MODERN
    animation: AnimationOption = AnimationOption.MEDIUM
    theme: ThemeOption = ThemeOption.LIGHT
    cta: str = ""
    image_source: ImageSource = ImageSource.PLACEHOLDER
    palette_id: PaletteId = PaletteId.AI_CHOICE
    custom_palette: ColorSwatch | None = None
    font_pairing_id: FontPairingId = FontPairingId.AI_CHOICE
    custom_fonts: FontChoice | None = None

    @model_validator(mode="after")
    def validate_custom_choices(self) -> Self:
        if (self.palette_id is PaletteId.CUSTOM) != (self.custom_palette is not None):
            raise ValueError("customPalette must be set only when paletteId is 'custom'")
        if (self.font_pairing_id is FontPairingId.CUSTOM) != (self.custom_fonts is not None):
            raise ValueError("customFonts must be set only when fontPairingId is 'custom'")
        return self
