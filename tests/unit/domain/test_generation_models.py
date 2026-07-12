from launchkit.domain.models import (
    BuiltPage,
    GenerationProvider,
    PipelineResult,
    PipelineStatus,
    PlannedPage,
    PlannedPageImage,
    SiteCopy,
    SiteCopySection,
    SitePlan,
    V0GenerationResult,
)


def test_nested_generation_result_preserves_shape_and_order() -> None:
    page = PlannedPage(
        name="Home",
        slug="index",
        is_home=True,
        purpose="Introduce the company",
        sections=["Hero", "Services"],
        images=[PlannedPageImage(section="Hero", desc="Team at work")],
    )
    plan = SitePlan(pages=[page], raw="1. Home")
    result = PipelineResult(
        provider=GenerationProvider.BOTH,
        pages=[BuiltPage(name="Home", slug="index", filename="index.html", html="<html></html>")],
        site_copy=SiteCopy(
            headline="Build faster",
            subheadline="A clear promise",
            sections=[SiteCopySection(heading="Services", body="Automation")],
            call_to_action="Contact us",
        ),
        v0=V0GenerationResult(
            chat_id="chat_1",
            web_url="https://v0.dev/chat_1",
            demo_url=None,
            status=PipelineStatus.COMPLETED,
            file_count=1,
        ),
        warnings=[],
    )

    assert plan.pages[0].sections == ["Hero", "Services"]
    payload = result.model_dump(by_alias=True, mode="json")
    assert payload["siteCopy"]["callToAction"] == "Contact us"
    assert payload["v0"]["fileCount"] == 1
