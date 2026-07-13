"""Repair dead interactions, repeated media, and duplicate navigation."""

import re
from typing import Final

_CTA_WORDS: Final = re.compile(
    r"order|book|reserve|contact|call|get in touch|enquir|inquir|get started|buy",
    re.IGNORECASE,
)
_ANCHOR: Final = re.compile(
    r"<a([^>]*?)href=[\"']#[^\"']*[\"']([^>]*)>([\s\S]*?)</a>",
    re.IGNORECASE,
)
_BUTTON: Final = re.compile(r"<button([^>]*)>([\s\S]*?)</button>", re.IGNORECASE)
_HTML_TAG: Final = re.compile(r"<[^>]+>")
_IMAGE: Final = re.compile(r"<img[^>]*>", re.IGNORECASE)
_IMAGE_SOURCE: Final = re.compile(r"src=[\"']([^\"']+)[\"']", re.IGNORECASE)
_BREADCRUMB: Final = re.compile(
    r"<(nav|div|ol|ul)\b[^>]*(?:breadcrumb|aria-label=[\"']breadcrumb)[^>]*>"
    r"[\s\S]*?</\1>",
    re.IGNORECASE,
)
_NAVIGATION: Final = re.compile(r"<nav\b[\s\S]*?</nav>", re.IGNORECASE)
_FOOTER: Final = re.compile(r"<footer\b[\s\S]*?</footer>", re.IGNORECASE)

_DUPLICATE_IMAGE_PANEL: Final = (
    '<div aria-hidden="true" style="width:100%;min-height:220px;border-radius:1rem;'
    'background:linear-gradient(135deg, rgba(0,0,0,.08), rgba(0,0,0,.22));"></div>'
)


def fix_ctas(html: str, order_page_href: str) -> str:
    """Route dead CTA anchors and unwired CTA buttons to the order page."""

    repaired = (
        html.replace('href="#"', f'href="{order_page_href}"')
        .replace("href='#'", f"href='{order_page_href}'")
        .replace('href=""', f'href="{order_page_href}"')
    )

    def repair_anchor(match: re.Match[str]) -> str:
        before, after, inner = match.groups()
        text = _HTML_TAG.sub("", inner)
        if _CTA_WORDS.search(text):
            return f'<a{before}href="{order_page_href}"{after}>{inner}</a>'
        return match.group(0)

    repaired = _ANCHOR.sub(repair_anchor, repaired)

    def repair_button(match: re.Match[str]) -> str:
        attrs, inner = match.groups()
        plain = _HTML_TAG.sub("", inner)
        attrs_lower = attrs.lower()
        already_wired = (
            "onclick" in attrs_lower
            or 'type="submit"' in attrs_lower
            or "type='submit'" in attrs_lower
        )
        if _CTA_WORDS.search(plain) and not already_wired:
            return (
                f"<button{attrs} onclick=\"window.location.href='{order_page_href}'\">"
                f"{inner}</button>"
            )
        return match.group(0)

    return _BUTTON.sub(repair_button, repaired)


def fix_duplicate_images(html: str) -> str:
    """Keep the first use of each image source and replace later occurrences."""

    seen: dict[str, int] = {}

    def repair_image(match: re.Match[str]) -> str:
        tag = match.group(0)
        source_match = _IMAGE_SOURCE.search(tag)
        if source_match is None:
            return tag
        source = source_match.group(1)
        seen[source] = seen.get(source, 0) + 1
        return _DUPLICATE_IMAGE_PANEL if seen[source] > 1 else tag

    return _IMAGE.sub(repair_image, html)


def strip_breadcrumbs(html: str) -> str:
    """Remove breadcrumb bars and non-footer navigation after the first nav."""

    repaired = _BREADCRUMB.sub("", html)
    navigations = list(_NAVIGATION.finditer(repaired))
    if len(navigations) <= 1:
        return repaired

    footer = _FOOTER.search(repaired)
    footer_start = footer.start() if footer is not None else -1
    footer_end = footer.end() if footer is not None else -1
    for navigation in reversed(navigations[1:]):
        start = navigation.start()
        inside_footer = footer_start != -1 and footer_start <= start <= footer_end
        if not inside_footer:
            repaired = repaired[:start] + repaired[navigation.end() :]
    return repaired
