"""Customer-readable rendering for planned pages."""

from collections.abc import Sequence

from launchkit.planning.models import PlannedPage


def render_plan_text(pages: Sequence[PlannedPage]) -> str:
    rendered_pages: list[str] = []
    for index, page in enumerate(pages, start=1):
        purpose = f"  —  {page.purpose}" if page.purpose else ""
        lines = [f"{index}. {page.name}{purpose}"]
        if page.sections:
            lines.append("     sections: " + " · ".join(page.sections))
        rendered_pages.append("\n".join(lines))
    return "\n\n".join(rendered_pages)
