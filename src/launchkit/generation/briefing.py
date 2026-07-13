"""Canonical grounded brief preparation."""

from launchkit.design.industry import get_industry_style_direction
from launchkit.design.models import DesignPreferences
from launchkit.generation.contracts import TextGenerator
from launchkit.generation.prompts import build_brief
from launchkit.intake.models import OnboardingForm


class BriefService:
    """Compute one tailored direction and deterministic grounded brief."""

    def __init__(self, generator: TextGenerator) -> None:
        self._generator = generator

    async def prepare(self, form: OnboardingForm, design: DesignPreferences) -> str:
        direction = await get_industry_style_direction(form, self._generator)
        return build_brief(form, design, direction)
