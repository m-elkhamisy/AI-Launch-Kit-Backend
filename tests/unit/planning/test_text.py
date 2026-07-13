from launchkit.planning import PlannedPage, render_plan_text


def test_render_plan_text_matches_typescript_format() -> None:
    pages = [
        PlannedPage(
            name="Home",
            slug="index",
            is_home=True,
            purpose="Introduce the company",
            sections=["Hero", "Services"],
            images=[],
        ),
        PlannedPage(
            name="Contact",
            slug="contact",
            is_home=False,
            purpose="",
            sections=[],
            images=[],
        ),
    ]

    assert render_plan_text(pages) == (
        "1. Home  —  Introduce the company\n     sections: Hero · Services\n\n2. Contact"
    )


def test_render_plan_text_accepts_an_empty_sequence() -> None:
    assert render_plan_text(()) == ""
