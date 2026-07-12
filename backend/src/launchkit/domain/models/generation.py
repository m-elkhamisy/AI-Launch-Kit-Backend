"""Generation-stage inputs and normalized results."""

from enum import StrEnum

from launchkit.domain.models.base import DomainModel


class GenerationProvider(StrEnum):
    V0 = "v0"
    CLAUDE = "claude"
    BOTH = "both"


class PipelineStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class MockupDesign(DomainModel):
    id: int
    label: str
    direction: str
    html: str


class SiteCopySection(DomainModel):
    heading: str
    body: str


class SiteCopy(DomainModel):
    headline: str
    subheadline: str
    sections: list[SiteCopySection]
    call_to_action: str


class BuiltPage(DomainModel):
    name: str
    slug: str
    filename: str
    html: str


class V0GenerationResult(DomainModel):
    chat_id: str
    web_url: str
    demo_url: str | None
    status: PipelineStatus
    file_count: int


class PipelineResult(DomainModel):
    provider: GenerationProvider
    pages: list[BuiltPage]
    site_copy: SiteCopy | None
    v0: V0GenerationResult | None
    warnings: list[str]
