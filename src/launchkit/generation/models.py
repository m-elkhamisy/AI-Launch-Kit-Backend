"""Generation-stage inputs and normalized results."""

from enum import StrEnum

from launchkit.core.models import AliasedModel


class GenerationProvider(StrEnum):
    V0 = "v0"
    CLAUDE = "claude"
    BOTH = "both"


class PipelineStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class MockupDesign(AliasedModel):
    id: int
    label: str
    direction: str
    html: str


class SiteCopySection(AliasedModel):
    heading: str
    body: str


class SiteCopy(AliasedModel):
    headline: str
    subheadline: str
    sections: list[SiteCopySection]
    call_to_action: str


class BuiltPage(AliasedModel):
    name: str
    slug: str
    filename: str
    html: str


class V0GenerationResult(AliasedModel):
    chat_id: str
    web_url: str
    demo_url: str | None
    status: PipelineStatus
    file_count: int


class PipelineResult(AliasedModel):
    provider: GenerationProvider
    pages: list[BuiltPage]
    site_copy: SiteCopy | None
    v0: V0GenerationResult | None
    warnings: list[str]
