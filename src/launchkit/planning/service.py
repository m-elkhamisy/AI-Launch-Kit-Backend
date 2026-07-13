"""Model-assisted site planning using deterministic normalization."""

from launchkit.design.models import DesignPreferences
from launchkit.generation.briefing import BriefService
from launchkit.generation.contracts import TextGenerator
from launchkit.generation.prompts import build_plan_prompt
from launchkit.images import ImageRegistry
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import SitePlan
from launchkit.planning.normalization import parse_site_plan


class SitePlanningService:
    def __init__(self, brief_service: BriefService, generator: TextGenerator) -> None:
        self._brief_service = brief_service
        self._generator = generator

    async def generate(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        chosen_mockup_html: str,
        *,
        feedback: str | None = None,
        previous_plan: SitePlan | None = None,
    ) -> SitePlan:
        brief = await self._brief_service.prepare(form, design)
        compressed = ImageRegistry().compress(chosen_mockup_html)
        response = await self._generator.generate_text(
            build_plan_prompt(brief, compressed, feedback, previous_plan), max_tokens=2_500
        )
        return parse_site_plan(response)
