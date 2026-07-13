"""Mockup generation and guaranteed fallback tests."""

import asyncio

from launchkit.design.models import DesignPreferences
from launchkit.generation.briefing import BriefService
from launchkit.generation.html_generation import HtmlGenerationService
from launchkit.generation.mockups import MockupGenerationService, fallback_mockup
from launchkit.intake.models import OnboardingForm


class TextStub:
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del system, model, temperature
        if max_tokens == 220:
            return "Tailored direction"
        return "incomplete"


def test_mockup_service_returns_three_visible_fallbacks() -> None:
    form = OnboardingForm(
        company_name="Acme <Co>",
        industry="Tech",
        business_activity="Software",
        target_audience="Teams",
    )
    design = DesignPreferences(tagline='Ship "fast"', cta="Start")
    generator = TextStub()
    service = MockupGenerationService(BriefService(generator), HtmlGenerationService(generator))

    result = asyncio.run(service.generate(form, design, []))

    assert [mockup.id for mockup in result.mockups] == [1, 2, 3]
    assert all(mockup.html.startswith("<!DOCTYPE html>") for mockup in result.mockups)
    assert "Acme &lt;Co&gt;" in result.mockups[0].html
    assert "Ship &quot;fast&quot;" in result.mockups[0].html
    assert "tailored" in result.brief


def test_fallback_mockup_includes_preview_image_and_cycles_palette() -> None:
    html = fallback_mockup(
        4,
        OnboardingForm(company_name="Acme"),
        DesignPreferences(),
        "data:image/png;base64,abc",
    )
    assert 'src="data:image/png;base64,abc"' in html
    assert "#FAF4EC" in html
