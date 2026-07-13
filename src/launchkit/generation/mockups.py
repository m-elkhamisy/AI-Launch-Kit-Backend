"""Generate three distinct design mockups with guaranteed local fallbacks."""

# ruff: noqa: E501

import asyncio
import html

from launchkit.design.models import DesignPreferences, ImageSource
from launchkit.generation.briefing import BriefService
from launchkit.generation.contracts import ImageGenerator, ImageSearch
from launchkit.generation.html_generation import HtmlGenerationService, html_looks_complete
from launchkit.generation.models import MockupDesign, MockupGenerationResult
from launchkit.generation.prompts import build_mockup_prompt
from launchkit.images import ImageRegistry, is_real_image, source_images_for_page
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import PlannedPageImage
from launchkit.profiles.models import ExtractedImage

MOCKUP_DIRECTIONS = (
    (
        "Editorial & elegant",
        "Direction A: editorial & elegant - large serif headlines, lots of whitespace, refined.",
    ),
    (
        "Bold & modern",
        "Direction B: bold & modern - big type, strong color blocks, confident and punchy.",
    ),
    (
        "Sleek & premium dark",
        "Direction C: sleek & premium dark - dark background, glowing accents, high-end tech feel.",
    ),
)
FALLBACK_PALETTES = (
    ("#0B1020", "#00C2FF", "#FFFFFF"),
    ("#FAF4EC", "#C9A24B", "#2B1D14"),
    ("#101418", "#7C4DFF", "#F5F5F5"),
)


class MockupGenerationService:
    def __init__(
        self,
        brief_service: BriefService,
        html_generator: HtmlGenerationService,
        *,
        image_generator: ImageGenerator | None = None,
        image_search: ImageSearch | None = None,
    ) -> None:
        self._brief_service = brief_service
        self._html_generator = html_generator
        self._image_generator = image_generator
        self._image_search = image_search

    async def generate(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        uploaded_images: list[ExtractedImage],
    ) -> MockupGenerationResult:
        brief = await self._brief_service.prepare(form, design)
        preview = await self._preview_image(form, design, uploaded_images)
        registry = ImageRegistry()
        prompt_preview = registry.compress(preview) if preview else None

        async def one(index: int, label: str, direction: str) -> MockupDesign:
            try:
                generated = await self._html_generator.generate(
                    build_mockup_prompt(direction, brief, prompt_preview), max_tokens=6_000
                )
                generated = registry.resolve(generated)
            except Exception:
                generated = ""
            if not html_looks_complete(generated):
                generated = fallback_mockup(index, form, design, preview)
            return MockupDesign(id=index + 1, label=label, direction=direction, html=generated)

        mockups = await asyncio.gather(
            *(
                one(index, label, direction)
                for index, (label, direction) in enumerate(MOCKUP_DIRECTIONS)
            )
        )
        return MockupGenerationResult(mockups=list(mockups), brief=brief)

    async def _preview_image(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        uploaded: list[ExtractedImage],
    ) -> str | None:
        if design.image_source is ImageSource.PLACEHOLDER:
            return None
        images = await source_images_for_page(
            [
                PlannedPageImage(
                    section="hero",
                    desc=f"A professional hero photo representing {form.industry} ({form.company_name})",
                )
            ],
            image_source=design.image_source,
            industry=form.industry,
            company_name=form.company_name,
            uploaded=uploaded,
            image_generator=self._image_generator,
            image_search=self._image_search,
        )
        return images[0].src if images and is_real_image(images[0].src) else None


def fallback_mockup(
    index: int,
    form: OnboardingForm,
    design: DesignPreferences,
    preview_image_url: str | None,
) -> str:
    bg, accent, foreground = FALLBACK_PALETTES[index % len(FALLBACK_PALETTES)]
    company = html.escape(form.company_name or "Your company", quote=True)
    industry = html.escape(form.industry, quote=True)
    headline = html.escape(
        design.tagline.strip() or form.company_name or "Your company", quote=True
    )
    activity = form.business_activity or form.industry or "What we do"
    audience = form.target_audience or "your customers"
    subline = html.escape(f"{activity} - built for {audience}.", quote=True)
    cta = html.escape(design.cta.strip() or "Get in touch", quote=True)
    image = (
        f'<img src="{html.escape(preview_image_url, quote=True)}" alt="" '
        'style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.25">'
        if preview_image_url
        else ""
    )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{company}</title></head>
<body style="margin:0;background:{bg};color:{foreground};font-family:system-ui">
<nav style="display:flex;justify-content:space-between;padding:18px 40px"><strong>{company}</strong><a href="#" style="color:{foreground}">{cta}</a></nav>
<section style="position:relative;min-height:620px;display:flex;align-items:center">{image}<div style="position:relative;max-width:640px;padding:60px 40px"><div style="color:{accent}">{industry}</div><h1 style="font-size:56px">{headline}</h1><p>{subline}</p><a href="#" style="background:{accent};color:{bg};padding:14px 26px">{cta}</a></div></section></body></html>"""
