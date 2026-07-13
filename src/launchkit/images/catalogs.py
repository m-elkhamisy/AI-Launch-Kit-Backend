"""Build per-page image catalogs while preserving upload rotation."""

from collections.abc import Sequence

from launchkit.design.models import DesignPreferences, ImageSource
from launchkit.generation.contracts import ImageGenerator, ImageSearch
from launchkit.images.registry import ImageRegistry
from launchkit.images.sourcing import render_image_catalog, source_images_for_page
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import PlannedPageImage, SitePlan
from launchkit.profiles.models import ExtractedImage


class ImageCatalogService:
    """Resolve every approved page's image plan into prompt instructions."""

    def __init__(
        self,
        *,
        image_generator: ImageGenerator | None = None,
        image_search: ImageSearch | None = None,
    ) -> None:
        self._image_generator = image_generator
        self._image_search = image_search

    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
        registry: ImageRegistry | None = None,
    ) -> dict[str, str]:
        offset = 0
        catalogs: dict[str, str] = {}
        for page in plan.pages:
            specs = page.images
            if design.image_source is not ImageSource.PLACEHOLDER and not specs:
                section = page.sections[0] if page.sections else "main section"
                specs = [
                    PlannedPageImage(
                        section=section,
                        desc=f"{form.industry} - photo for the {page.name} page ({section})",
                    )
                ]
            sourced = await source_images_for_page(
                specs,
                image_source=design.image_source,
                industry=form.industry,
                company_name=form.company_name,
                uploaded=uploaded_images,
                uploaded_offset=offset,
                image_generator=self._image_generator,
                image_search=self._image_search,
            )
            offset += len(specs)
            catalogs[page.name] = render_image_catalog(sourced, registry)
        return catalogs
