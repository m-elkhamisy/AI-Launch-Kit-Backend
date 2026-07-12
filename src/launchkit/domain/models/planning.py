"""Generated site and page planning models."""

from launchkit.domain.models.base import DomainModel


class PlannedPageImage(DomainModel):
    section: str
    desc: str


class PlannedPage(DomainModel):
    name: str
    slug: str
    is_home: bool
    purpose: str
    sections: list[str]
    images: list[PlannedPageImage]


class SitePlan(DomainModel):
    pages: list[PlannedPage]
    raw: str
