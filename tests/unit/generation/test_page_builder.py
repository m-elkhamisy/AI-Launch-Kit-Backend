"""Multi-page build coordination tests."""

import asyncio

import pytest

from launchkit.core.exceptions import DomainError
from launchkit.design.models import DesignPreferences, ImageSource
from launchkit.generation.html_generation import HtmlGenerationService
from launchkit.generation.page_builder import PageBuildService
from launchkit.intake.models import OnboardingForm
from launchkit.planning.models import PlannedPage, SitePlan
from launchkit.profiles.models import ExtractedImage


def complete_page(label: str) -> str:
    return (
        "<!DOCTYPE html><html><body><nav>Shared nav</nav>"
        f'<h1>{label}</h1><a href="#">Contact</a>{"x" * 2600}'
        "<footer>Shared footer</footer></body></html>"
    )


class PageTextStub:
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 4_000,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        del system, max_tokens, model, temperature
        if '"Fail" page' in prompt:
            raise RuntimeError("generation failed")
        if "HOMEPAGE" in prompt:
            return complete_page("Home")
        assert "Shared nav" in prompt
        return complete_page("About")


def planned(name: str, slug: str, home: bool = False) -> PlannedPage:
    return PlannedPage(
        name=name,
        slug=slug,
        is_home=home,
        purpose="",
        sections=["Overview"],
        images=[],
    )


def test_page_builder_builds_home_first_and_warns_for_failed_secondary() -> None:
    service = PageBuildService(HtmlGenerationService(PageTextStub()))
    plan = SitePlan(
        pages=[planned("Home", "index", True), planned("About", "about"), planned("Fail", "fail")],
        raw="plan",
    )
    uploaded = [
        ExtractedImage(
            filename="logo.png", label="Company Logo", data_url="data:image/png;base64,YWJj"
        )
    ]

    result = asyncio.run(
        service.build(
            OnboardingForm(company_name="Acme", industry="Tech"),
            DesignPreferences(image_source=ImageSource.UPLOADED),
            "brief",
            "mockup",
            plan,
            uploaded,
        )
    )

    assert [page.filename for page in result.pages] == ["index.html", "about.html"]
    assert len(result.warnings) == 1
    assert '"Fail"' in result.warnings[0]
    assert 'href="fail.html"' in result.pages[0].html
    assert "data:image/png;base64,YWJj" in result.pages[0].html


def test_page_builder_rejects_empty_plan() -> None:
    service = PageBuildService(HtmlGenerationService(PageTextStub()))
    with pytest.raises(DomainError):
        asyncio.run(
            service.build(
                OnboardingForm(),
                DesignPreferences(),
                "brief",
                "mockup",
                SitePlan(pages=[], raw=""),
                [],
            )
        )
