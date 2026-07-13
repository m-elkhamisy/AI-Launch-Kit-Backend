"""Deterministic processing for generated HTML documents."""

from launchkit.html.injections import AOS_FAILSAFE, inject_aos_failsafe, inject_favicon
from launchkit.html.processing import postprocess_html
from launchkit.html.repairs import fix_ctas, fix_duplicate_images, strip_breadcrumbs
from launchkit.html.tailwind import fix_tailwind_classes

__all__ = [
    "AOS_FAILSAFE",
    "fix_ctas",
    "fix_duplicate_images",
    "fix_tailwind_classes",
    "inject_aos_failsafe",
    "inject_favicon",
    "postprocess_html",
    "strip_breadcrumbs",
]
