"""Coordinate multi-page HTML generation from an approved plan."""

import asyncio
import re
from collections.abc import Sequence

from launchkit.core.exceptions import DomainError
from launchkit.design.models import DesignPreferences
from launchkit.generation.contracts import ImageGenerator, ImageSearch
from launchkit.generation.html_generation import HtmlGenerationService
from launchkit.generation.models import BuiltPage, PageBuildResult
from launchkit.generation.prompts import (
    build_forbidden_sections,
    build_page_prompt,
    build_page_summary,
)
from launchkit.html import postprocess_html
from launchkit.images import ImageCatalogService, ImageRegistry
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import PlannedPage, SitePlan
from launchkit.profiles.models import ExtractedImage

ORDER_KEYWORDS = (
    "order",
    "contact",
    "book",
    "reserve",
    "visit",
    "get in touch",
    "enquir",
    "inquir",
)
PAGE_MIN_CHARS = 2_500


class PageBuildService:
    """Build the homepage shell first, then isolated secondary pages."""

    def __init__(
        self,
        html_generator: HtmlGenerationService,
        *,
        image_generator: ImageGenerator | None = None,
        image_search: ImageSearch | None = None,
        secondary_concurrency: int = 2,
    ) -> None:
        self._html_generator = html_generator
        self._catalogs = ImageCatalogService(
            image_generator=image_generator,
            image_search=image_search,
        )
        self._secondary_concurrency = max(1, secondary_concurrency)

    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        brief: str,
        chosen_mockup_html: str,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
    ) -> PageBuildResult:
        if not plan.pages:
            raise DomainError("Cannot build a website without planned pages")
        registry = ImageRegistry()
        catalogs = await self._catalogs.build(form, design, plan, uploaded_images, registry)
        compressed_mockup = registry.compress(chosen_mockup_html)
        logo = next(
            (image.data_url for image in uploaded_images if "logo" in image.label.lower()),
            None,
        )
        order_page = self._find_order_page(plan.pages)
        order_href = f"{order_page.slug}.html"
        site_map = build_page_summary(plan.pages)
        cta_rule = (
            f'Every primary call-to-action button (e.g. "{design.cta or "Contact us"}", '
            f'"Order", "Book", "Contact") MUST link to "{order_href}".'
        )
        home = next((page for page in plan.pages if page.is_home), plan.pages[0])
        home_prompt = self._page_prompt(
            home,
            True,
            brief,
            compressed_mockup,
            plan,
            site_map,
            catalogs,
            cta_rule,
            order_page,
            design,
            "",
            "",
        )
        home_html = await self._html_generator.generate(home_prompt, min_chars=PAGE_MIN_CHARS)
        home_html = postprocess_html(registry.resolve(home_html), order_href, logo)
        navigation, footer = _extract_shell(home_html)
        compressed_navigation = registry.compress(navigation)
        compressed_footer = registry.compress(footer)

        semaphore = asyncio.Semaphore(self._secondary_concurrency)

        async def build_secondary(page: PlannedPage) -> tuple[BuiltPage | None, str | None]:
            async with semaphore:
                try:
                    prompt = self._page_prompt(
                        page,
                        False,
                        brief,
                        compressed_mockup,
                        plan,
                        site_map,
                        catalogs,
                        cta_rule,
                        order_page,
                        design,
                        compressed_navigation,
                        compressed_footer,
                    )
                    generated = await self._html_generator.generate(
                        prompt, min_chars=PAGE_MIN_CHARS
                    )
                    processed = postprocess_html(registry.resolve(generated), order_href, logo)
                    return (
                        BuiltPage(
                            name=page.name,
                            slug=page.slug,
                            filename=f"{page.slug}.html",
                            html=processed,
                        ),
                        None,
                    )
                except Exception as exc:
                    return None, f'Couldn\'t build the "{page.name}" page: {exc}'

        secondary = [page for page in plan.pages if page.slug != home.slug]
        outcomes = await asyncio.gather(*(build_secondary(page) for page in secondary))
        pages = [BuiltPage(name=home.name, slug="index", filename="index.html", html=home_html)]
        pages.extend(page for page, _warning in outcomes if page is not None)
        warnings = [warning for _page, warning in outcomes if warning is not None]
        return PageBuildResult(pages=pages, warnings=warnings)

    @staticmethod
    def _find_order_page(pages: Sequence[PlannedPage]) -> PlannedPage:
        return next(
            (
                page
                for page in pages
                if any(keyword in page.name.lower() for keyword in ORDER_KEYWORDS)
            ),
            pages[-1],
        )

    @staticmethod
    def _page_prompt(
        page: PlannedPage,
        is_home: bool,
        brief: str,
        chosen_mockup_html: str,
        plan: SitePlan,
        site_map: str,
        catalogs: dict[str, str],
        cta_rule: str,
        order_page: PlannedPage,
        design: DesignPreferences,
        nav_html: str,
        footer_html: str,
    ) -> str:
        return build_page_prompt(
            page=page,
            is_home=is_home,
            brief=brief,
            chosen_mockup_html=chosen_mockup_html,
            site_map=site_map,
            image_catalog=catalogs.get(page.name, ""),
            cta_rule=cta_rule,
            nav_html=nav_html,
            footer_html=footer_html,
            forbidden_sections=build_forbidden_sections(plan.pages, page.name),
            is_order_page=page.slug == order_page.slug,
            theme=design.theme.value,
        )


def _extract_shell(html: str) -> tuple[str, str]:
    navigation = re.search(r"<nav\b[\s\S]*?</nav>", html, flags=re.IGNORECASE)
    footer = re.search(r"<footer\b[\s\S]*?</footer>", html, flags=re.IGNORECASE)
    return navigation.group(0) if navigation else "", footer.group(0) if footer else ""
