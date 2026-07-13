"""Compose generated-HTML processing in the preserved source order."""

from launchkit.html.injections import inject_aos_failsafe, inject_favicon
from launchkit.html.repairs import fix_ctas, fix_duplicate_images, strip_breadcrumbs
from launchkit.html.tailwind import fix_tailwind_classes


def postprocess_html(
    html: str,
    order_page_href: str,
    favicon_href: str | None = None,
    *,
    normalize_tailwind: bool = False,
) -> str:
    """Apply canonical repairs, optional Karim normalization, and document injections."""

    repaired = fix_ctas(html, order_page_href)
    repaired = fix_duplicate_images(repaired)
    repaired = strip_breadcrumbs(repaired)
    if normalize_tailwind:
        repaired = fix_tailwind_classes(repaired)
    if favicon_href:
        repaired = inject_favicon(repaired, favicon_href)
    return inject_aos_failsafe(repaired)
