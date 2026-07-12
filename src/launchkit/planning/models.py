"""Generated site and page planning models."""

from launchkit.core.models import AliasedModel


class PlannedPageImage(AliasedModel):
    section: str
    desc: str


class PlannedPage(AliasedModel):
    name: str
    slug: str
    is_home: bool
    purpose: str
    sections: list[str]
    images: list[PlannedPageImage]


class SitePlan(AliasedModel):
    pages: list[PlannedPage]
    raw: str
