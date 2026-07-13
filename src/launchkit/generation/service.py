"""Provider-neutral orchestration of an approved website generation request."""

from collections.abc import Mapping, Sequence
from typing import Protocol

from launchkit.core.exceptions import ConfigurationError
from launchkit.design.models import DesignPreferences
from launchkit.generation.models import (
    BuiltPage,
    GenerationProvider,
    PageBuildResult,
    PipelineResult,
    SiteCopy,
    V0ChatPrivacy,
    V0GenerationResult,
    WebsiteGenerationRequest,
)
from launchkit.generation.prompts import build_v0_multi_page_brief
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import SitePlan
from launchkit.profiles.models import ExtractedImage


class BriefPreparer(Protocol):
    async def prepare(self, form: OnboardingForm, design: DesignPreferences) -> str:
        """Prepare one canonical brief."""


class PageBuilder(Protocol):
    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        brief: str,
        chosen_mockup_html: str,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
    ) -> PageBuildResult:
        """Build generated HTML pages."""


class CopyExtractor(Protocol):
    async def extract(self, homepage_html: str) -> SiteCopy | None:
        """Extract best-effort copy from a built homepage."""


class CatalogBuilder(Protocol):
    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
        registry: object | None = None,
    ) -> Mapping[str, str]:
        """Build per-page image instructions."""


class V0Gateway(Protocol):
    async def create_chat(
        self,
        prompt: str,
        *,
        privacy: V0ChatPrivacy = V0ChatPrivacy.PRIVATE,
    ) -> V0GenerationResult:
        """Generate a site from a written brief."""

    async def host_pages(
        self,
        pages: Sequence[BuiltPage],
        company_name: str,
    ) -> V0GenerationResult:
        """Host exact generated HTML files."""


class WebsiteGenerationService:
    """Select provider mode and coordinate already-tested capabilities."""

    def __init__(
        self,
        brief_service: BriefPreparer,
        page_builder: PageBuilder,
        copy_extractor: CopyExtractor,
        image_catalogs: CatalogBuilder,
        *,
        v0: V0Gateway | None = None,
    ) -> None:
        self._brief_service = brief_service
        self._page_builder = page_builder
        self._copy_extractor = copy_extractor
        self._image_catalogs = image_catalogs
        self._v0 = v0

    async def generate(self, request: WebsiteGenerationRequest) -> PipelineResult:
        brief = await self._brief_service.prepare(request.form, request.design)
        if request.provider is GenerationProvider.V0:
            v0 = self._require_v0()
            catalogs = await self._image_catalogs.build(
                request.form,
                request.design,
                request.plan,
                request.uploaded_images,
            )
            prompt = build_v0_multi_page_brief(
                brief,
                request.chosen_mockup_html,
                request.plan.pages,
                catalogs,
            )
            result = await v0.create_chat(prompt)
            return PipelineResult(
                provider=request.provider,
                pages=[],
                site_copy=None,
                v0=result,
                warnings=[],
            )

        built = await self._page_builder.build(
            request.form,
            request.design,
            brief,
            request.chosen_mockup_html,
            request.plan,
            request.uploaded_images,
        )
        site_copy = await self._copy_extractor.extract(built.pages[0].html) if built.pages else None
        warnings = list(built.warnings)
        hosted: V0GenerationResult | None = None
        if request.provider is GenerationProvider.BOTH:
            if self._v0 is None:
                warnings.append(
                    "v0 is not configured, so HTML was generated but v0 hosting was skipped."
                )
            else:
                try:
                    hosted = await self._v0.host_pages(
                        built.pages,
                        request.form.company_name,
                    )
                except Exception as exc:
                    warnings.append(f"HTML was generated, but v0 hosting failed: {exc}")
        return PipelineResult(
            provider=request.provider,
            pages=built.pages,
            site_copy=site_copy,
            v0=hosted,
            warnings=warnings,
        )

    def _require_v0(self) -> V0Gateway:
        if self._v0 is None:
            raise ConfigurationError("v0 is not configured for v0-based generation")
        return self._v0
