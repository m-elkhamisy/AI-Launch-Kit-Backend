"""Generation-stage inputs and normalized results."""

from enum import StrEnum

from launchkit.core.models import AliasedModel
from launchkit.design.models import DesignPreferences
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import SitePlan
from launchkit.profiles.models import ExtractedImage


class GenerationProvider(StrEnum):
    V0 = "v0"
    CLAUDE = "claude"
    BOTH = "both"


class PipelineStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class V0ChatPrivacy(StrEnum):
    PRIVATE = "private"
    UNLISTED = "unlisted"
    PUBLIC = "public"


class MockupDesign(AliasedModel):
    id: int
    label: str
    direction: str
    html: str


class MockupGenerationResult(AliasedModel):
    mockups: list[MockupDesign]
    brief: str


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


class PageBuildResult(AliasedModel):
    pages: list[BuiltPage]
    warnings: list[str]


class V0GenerationResult(AliasedModel):
    chat_id: str
    web_url: str | None
    demo_url: str | None
    status: PipelineStatus
    file_count: int


class V0HandoffResult(AliasedModel):
    chat_id: str
    claim_url: str
    privacy: V0ChatPrivacy | None


class ArchiveDownload(AliasedModel):
    content: bytes
    filename: str


class WebsiteGenerationRequest(AliasedModel):
    form: OnboardingForm
    design: DesignPreferences
    provider: GenerationProvider
    chosen_mockup_html: str
    plan: SitePlan
    uploaded_images: list[ExtractedImage]


class PipelineResult(AliasedModel):
    provider: GenerationProvider
    pages: list[BuiltPage]
    site_copy: SiteCopy | None
    v0: V0GenerationResult | None
    warnings: list[str]
