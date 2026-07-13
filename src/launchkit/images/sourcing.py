"""Resolve planned image specifications without producing broken image URLs."""

from collections.abc import Sequence

from launchkit.design.models import ImageSource
from launchkit.generation.contracts import ImageGenerator, ImageSearch
from launchkit.images.registry import ImageRegistry
from launchkit.planning.models import PlannedPageImage
from launchkit.profiles.models import ExtractedImage, SourcedImage

PANEL_SENTINEL = "__PANEL__"


def is_real_image(source: str) -> bool:
    return source != PANEL_SENTINEL


async def source_images_for_page(
    specs: Sequence[PlannedPageImage],
    *,
    image_source: ImageSource,
    industry: str,
    company_name: str,
    uploaded: Sequence[ExtractedImage] = (),
    uploaded_offset: int = 0,
    image_generator: ImageGenerator | None = None,
    image_search: ImageSearch | None = None,
) -> list[SourcedImage]:
    """Return one resolved image or panel sentinel for every plan specification."""

    results: list[SourcedImage] = []
    for index, spec in enumerate(specs):
        source = PANEL_SENTINEL
        credit: str | None = None
        if image_source is ImageSource.UPLOADED and uploaded:
            source = uploaded[(uploaded_offset + index) % len(uploaded)].data_url
        elif image_source is ImageSource.AI and image_generator is not None:
            try:
                source = await image_generator.generate_image(
                    "Generate a high-quality, photorealistic marketing photo for a website. "
                    f"{spec.desc}. Business: {company_name}, a {industry} business. "
                    "No text or watermarks in the image."
                )
            except Exception:
                source = PANEL_SENTINEL
        elif image_source is ImageSource.PEXELS and image_search is not None:
            try:
                found = await image_search.search_image(f"{spec.desc} {industry}")
            except Exception:
                found = None
            if found is not None:
                source, credit = found
        results.append(
            SourcedImage(
                section=spec.section,
                desc=spec.desc,
                src=source or PANEL_SENTINEL,
                alt=spec.desc,
                credit=credit,
            )
        )
    return results


def render_image_catalog(
    images: Sequence[SourcedImage],
    registry: ImageRegistry | None = None,
) -> str:
    """Render exact image placement instructions for a generated page."""

    if not images:
        return (
            "No images assigned to this page - use styled color/gradient panels or icon "
            "compositions instead, per the design system."
        )
    lines: list[str] = []
    for image in images:
        if image.src == PANEL_SENTINEL:
            lines.append(
                f'- "{image.section}" section: NO image available - render a styled '
                f"gradient/color panel here ({image.desc}), never a broken <img> tag or an "
                "external URL."
            )
        else:
            source = registry.compress(image.src) if registry else image.src
            lines.append(
                f'- "{image.section}" section: use exactly this image src="{source}" '
                f'alt="{image.alt}" ({image.desc})'
            )
    return (
        "IMAGES FOR THIS PAGE - use each EXACTLY ONCE, in its named section, using the exact "
        "src given. Never reuse the same src twice on one page, never invent a different "
        "external image URL:\n" + "\n".join(lines)
    )
