"""Deterministic normalization of model-produced site plans."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from launchkit.core.exceptions import DomainError
from launchkit.planning.models import PlannedPage, PlannedPageImage, SitePlan
from launchkit.planning.text import render_plan_text


class SitePlanError(DomainError):
    """Raised when generated planning output cannot form a site plan."""


def strip_code_fence(value: str) -> str:
    """Remove one Markdown code fence around a model response."""

    cleaned = value.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", cleaned).strip()


def slugify(value: str) -> str:
    """Return the source-compatible lowercase ASCII page slug."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "site"


def parse_site_plan(raw: str) -> SitePlan:
    """Parse and normalize JSON returned by the planning model."""

    try:
        payload = json.loads(strip_code_fence(raw))
    except (json.JSONDecodeError, TypeError) as exc:
        raise SitePlanError("The planning step returned invalid JSON - please try again.") from exc

    if not isinstance(payload, Mapping):
        raise SitePlanError("The planning step returned invalid JSON - please try again.")
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise SitePlanError("The planning step didn't return any pages - please try again.")
    return normalize_site_plan(pages)


def normalize_site_plan(pages: Sequence[Mapping[str, Any]]) -> SitePlan:
    """Apply Haseeb's page defaults, home selection, and slug de-duplication."""

    if not pages:
        raise SitePlanError("The planning step didn't return any pages - please try again.")

    home_index = next((index for index, page in enumerate(pages) if page.get("isHome")), 0)
    used_slugs: set[str] = set()
    normalized: list[PlannedPage] = []

    for index, page in enumerate(pages):
        name_value = page.get("name")
        name = name_value if isinstance(name_value, str) and name_value else f"Page {index + 1}"
        is_home = index == home_index
        candidate = "index" if is_home else slugify(name)
        base = candidate
        suffix = 2
        while candidate in used_slugs:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used_slugs.add(candidate)

        purpose_value = page.get("purpose")
        purpose = purpose_value if isinstance(purpose_value, str) else ""
        sections_value = page.get("sections")
        sections = (
            [str(section) for section in sections_value]
            if isinstance(sections_value, list) and sections_value
            else ["Overview"]
        )
        images_value = page.get("images")
        images = _normalize_images(images_value)
        normalized.append(
            PlannedPage(
                name=name,
                slug=candidate,
                is_home=is_home,
                purpose=purpose,
                sections=sections,
                images=images,
            )
        )

    return SitePlan(pages=normalized, raw=render_plan_text(normalized))


def _normalize_images(value: object) -> list[PlannedPageImage]:
    if not isinstance(value, list):
        return []
    images: list[PlannedPageImage] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        section = item.get("section")
        desc = item.get("desc")
        if isinstance(section, str) and isinstance(desc, str):
            images.append(PlannedPageImage(section=section, desc=desc))
    return images
