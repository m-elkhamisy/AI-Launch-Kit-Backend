"""Characterization tests for source-compatible site-plan normalization."""

import pytest

from launchkit.planning.normalization import (
    SitePlanError,
    normalize_site_plan,
    parse_site_plan,
    slugify,
)


def test_parse_site_plan_strips_json_fence_and_preserves_order() -> None:
    plan = parse_site_plan(
        '```json\n{"pages": ['
        '{"name":"About","isHome":false,"purpose":"Story","sections":["Team"],'
        '"images":[{"section":"Team","desc":"Team portrait"}]},'
        '{"name":"Welcome","isHome":true,"purpose":"","sections":[],"images":[]}'
        "]}\n```"
    )

    assert [page.name for page in plan.pages] == ["About", "Welcome"]
    assert [page.slug for page in plan.pages] == ["about", "index"]
    assert [page.is_home for page in plan.pages] == [False, True]
    assert plan.pages[1].sections == ["Overview"]
    assert plan.pages[0].images[0].desc == "Team portrait"
    assert "About" in plan.raw


@pytest.mark.parametrize("raw", ["not json", "[]", "{}", '{"pages":[]}'])
def test_parse_site_plan_rejects_invalid_or_empty_output(raw: str) -> None:
    with pytest.raises(SitePlanError):
        parse_site_plan(raw)


def test_normalize_site_plan_uses_first_page_as_home_and_source_defaults() -> None:
    plan = normalize_site_plan([{}, {"name": "Services"}])

    assert plan.pages[0].model_dump() == {
        "name": "Page 1",
        "slug": "index",
        "is_home": True,
        "purpose": "",
        "sections": ["Overview"],
        "images": [],
    }
    assert plan.pages[1].slug == "services"


def test_normalize_site_plan_rejects_empty_sequence() -> None:
    with pytest.raises(SitePlanError):
        normalize_site_plan([])


def test_normalize_site_plan_deduplicates_slugs_and_forces_one_home() -> None:
    plan = normalize_site_plan(
        [
            {"name": "Home", "isHome": True},
            {"name": "Index", "isHome": True},
            {"name": "Our Work"},
            {"name": "Our Work"},
            {"name": "!!!"},
        ]
    )

    assert [page.slug for page in plan.pages] == [
        "index",
        "index-2",
        "our-work",
        "our-work-2",
        "site",
    ]
    assert [page.is_home for page in plan.pages] == [True, False, False, False, False]


@pytest.mark.parametrize(
    ("value", "expected"),
    [("  About Us  ", "about-us"), ("Caf\u00e9 & Shop", "caf-shop"), ("---", "site")],
)
def test_slugify_matches_typescript_ascii_behavior(value: str, expected: str) -> None:
    assert slugify(value) == expected


def test_normalize_site_plan_ignores_malformed_image_items() -> None:
    plan = normalize_site_plan(
        [{"images": [None, {"section": "Hero"}, {"section": "Hero", "desc": "Photo"}]}]
    )

    assert [image.desc for image in plan.pages[0].images] == ["Photo"]
