"""Offline integration tests for all website generation provider modes."""

import asyncio
from collections.abc import Mapping, Sequence

import pytest

from launchkit.core.exceptions import ConfigurationError
from launchkit.design.models import DesignPreferences
from launchkit.generation import WebsiteGenerationRequest, WebsiteGenerationService
from launchkit.generation.models import (
    BuiltPage,
    GenerationProvider,
    PageBuildResult,
    PipelineStatus,
    SiteCopy,
    V0ChatPrivacy,
    V0GenerationResult,
)
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import PlannedPage, SitePlan
from launchkit.profiles.models import ExtractedImage


class BriefStub:
    async def prepare(self, form: OnboardingForm, design: DesignPreferences) -> str:
        del design
        return f"Brief for {form.company_name}"


class PageBuilderStub:
    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        brief: str,
        chosen_mockup_html: str,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
    ) -> PageBuildResult:
        del form, design, brief, chosen_mockup_html, plan, uploaded_images
        return PageBuildResult(
            pages=[BuiltPage(name="Home", slug="index", filename="index.html", html="home")],
            warnings=["secondary failed"],
        )


class CopyStub:
    async def extract(self, homepage_html: str) -> SiteCopy | None:
        assert homepage_html == "home"
        return SiteCopy(
            headline="Home",
            subheadline="",
            sections=[],
            call_to_action="Contact",
        )


class CatalogStub:
    async def build(
        self,
        form: OnboardingForm,
        design: DesignPreferences,
        plan: SitePlan,
        uploaded_images: Sequence[ExtractedImage],
        registry: object | None = None,
    ) -> Mapping[str, str]:
        del form, design, uploaded_images, registry
        return {page.name: "No images" for page in plan.pages}


class V0Stub:
    def __init__(self, *, host_error: Exception | None = None) -> None:
        self.host_error = host_error
        self.created_prompt = ""
        self.hosted: list[BuiltPage] = []

    @staticmethod
    def result() -> V0GenerationResult:
        return V0GenerationResult(
            chat_id="chat-1",
            web_url="https://v0/chat-1",
            demo_url=None,
            status=PipelineStatus.PENDING,
            file_count=0,
        )

    async def create_chat(
        self,
        prompt: str,
        *,
        privacy: V0ChatPrivacy = V0ChatPrivacy.PRIVATE,
    ) -> V0GenerationResult:
        assert privacy is V0ChatPrivacy.PRIVATE
        self.created_prompt = prompt
        return self.result()

    async def host_pages(self, pages: Sequence[BuiltPage], company_name: str) -> V0GenerationResult:
        assert company_name == "Acme"
        if self.host_error:
            raise self.host_error
        self.hosted = list(pages)
        return self.result()


def request(provider: GenerationProvider) -> WebsiteGenerationRequest:
    return WebsiteGenerationRequest(
        form=OnboardingForm(company_name="Acme", industry="Tech"),
        design=DesignPreferences(),
        provider=provider,
        chosen_mockup_html="mockup",
        plan=SitePlan(
            pages=[
                PlannedPage(
                    name="Home",
                    slug="index",
                    is_home=True,
                    purpose="",
                    sections=["Hero"],
                    images=[],
                )
            ],
            raw="plan",
        ),
        uploaded_images=[],
    )


def service(v0: V0Stub | None = None) -> WebsiteGenerationService:
    return WebsiteGenerationService(
        BriefStub(), PageBuilderStub(), CopyStub(), CatalogStub(), v0=v0
    )


def test_v0_mode_builds_provider_brief_without_html_pages() -> None:
    v0 = V0Stub()
    result = asyncio.run(service(v0).generate(request(GenerationProvider.V0)))

    assert result.pages == []
    assert result.v0 is not None
    assert "Brief for Acme" in v0.created_prompt
    assert "Home" in v0.created_prompt


def test_claude_mode_returns_pages_copy_and_build_warnings() -> None:
    result = asyncio.run(service().generate(request(GenerationProvider.CLAUDE)))

    assert result.pages[0].filename == "index.html"
    assert result.site_copy is not None and result.site_copy.headline == "Home"
    assert result.v0 is None
    assert result.warnings == ["secondary failed"]


def test_both_mode_hosts_exact_pages() -> None:
    v0 = V0Stub()
    result = asyncio.run(service(v0).generate(request(GenerationProvider.BOTH)))

    assert result.v0 is not None
    assert v0.hosted == result.pages


def test_both_mode_keeps_html_when_hosting_missing_or_fails() -> None:
    missing = asyncio.run(service().generate(request(GenerationProvider.BOTH)))
    failed = asyncio.run(
        service(V0Stub(host_error=RuntimeError("down"))).generate(request(GenerationProvider.BOTH))
    )

    assert missing.pages and "not configured" in missing.warnings[-1]
    assert failed.pages and "hosting failed: down" in failed.warnings[-1]


def test_v0_mode_requires_gateway() -> None:
    with pytest.raises(ConfigurationError):
        asyncio.run(service().generate(request(GenerationProvider.V0)))
