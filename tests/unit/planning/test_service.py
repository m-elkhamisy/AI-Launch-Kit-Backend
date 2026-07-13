"""Site planning service tests."""

import asyncio

from launchkit.design.models import DesignPreferences
from launchkit.generation.briefing import BriefService
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import SitePlan
from launchkit.planning.service import SitePlanningService


class TextStub:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del system, max_tokens, model, temperature
        self.prompts.append(prompt)
        return self.response


def test_planning_service_builds_brief_compresses_images_and_normalizes() -> None:
    brief_generator = TextStub("")
    plan_generator = TextStub('{"pages":[{"name":"Home","isHome":true},{"name":"Contact"}]}')
    service = SitePlanningService(BriefService(brief_generator), plan_generator)

    plan = asyncio.run(
        service.generate(
            OnboardingForm(company_name="Acme", industry="Tech"),
            DesignPreferences(),
            '<img src="data:image/png;base64,YWJj">',
        )
    )

    assert [page.slug for page in plan.pages] == ["index", "contact"]
    assert "__IMG_REF_1__" in plan_generator.prompts[0]


def test_planning_service_includes_revision_context() -> None:
    brief_generator = TextStub("")
    plan_generator = TextStub('{"pages":[{"name":"Home"}]}')
    previous = SitePlan(pages=[], raw="Previous plan")
    service = SitePlanningService(BriefService(brief_generator), plan_generator)

    asyncio.run(
        service.generate(
            OnboardingForm(),
            DesignPreferences(),
            "mockup",
            feedback="Add contact",
            previous_plan=previous,
        )
    )
    assert "Previous plan" in plan_generator.prompts[0]
    assert "Add contact" in plan_generator.prompts[0]
