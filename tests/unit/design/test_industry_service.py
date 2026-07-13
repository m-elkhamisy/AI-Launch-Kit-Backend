"""Tests for model-tailored industry direction with deterministic fallback."""

import asyncio

from launchkit.design.industry import get_industry_style_direction
from launchkit.intake.models import OnboardingForm


class GeneratorStub:
    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error

    async def generate_text(
        self,
        _prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del system, max_tokens, model, temperature
        if self.error:
            raise self.error
        return self.response


def test_industry_service_prefers_tailored_direction() -> None:
    form = OnboardingForm(company_name="Acme", industry="Robotics")

    result = asyncio.run(get_industry_style_direction(form, GeneratorStub("  precise grids  ")))

    assert result == "INDUSTRY STYLE DIRECTION (tailored): precise grids"


def test_industry_service_falls_back_on_empty_or_error() -> None:
    form = OnboardingForm(industry="Bakery")

    assert "(bakery)" in asyncio.run(get_industry_style_direction(form, GeneratorStub()))
    assert "(bakery)" in asyncio.run(
        get_industry_style_direction(form, GeneratorStub(error=RuntimeError("down")))
    )
