"""Source-compatible image resolution and catalog tests."""

import asyncio

import pytest

from launchkit.design.models import ImageSource
from launchkit.images import PANEL_SENTINEL, ImageRegistry, is_real_image
from launchkit.images.sourcing import render_image_catalog, source_images_for_page
from launchkit.planning.models import PlannedPageImage
from launchkit.profiles.models import ExtractedImage, SourcedImage

SPECS = [
    PlannedPageImage(section="Hero", desc="Bakery counter"),
    PlannedPageImage(section="Team", desc="Bakers"),
]


class ImageGeneratorStub:
    def __init__(self, result: str = "data:image/png;base64,abc", fail: bool = False) -> None:
        self.result = result
        self.fail = fail
        self.prompts: list[str] = []

    async def generate_image(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.fail:
            raise RuntimeError("down")
        return self.result


class ImageSearchStub:
    def __init__(self, result: tuple[str, str | None] | None = None, fail: bool = False) -> None:
        self.result = result
        self.fail = fail
        self.queries: list[str] = []

    async def search_image(self, query: str) -> tuple[str, str | None] | None:
        self.queries.append(query)
        if self.fail:
            raise RuntimeError("down")
        return self.result


def test_uploaded_images_rotate_from_running_offset() -> None:
    uploaded = [
        ExtractedImage(filename="a", label="a", data_url="data:a"),
        ExtractedImage(filename="b", label="b", data_url="data:b"),
    ]
    result = asyncio.run(
        source_images_for_page(
            SPECS,
            image_source=ImageSource.UPLOADED,
            industry="Bakery",
            company_name="Acme",
            uploaded=uploaded,
            uploaded_offset=1,
        )
    )

    assert [image.src for image in result] == ["data:b", "data:a"]


@pytest.mark.parametrize("fail", [False, True])
def test_ai_source_returns_generated_image_or_panel(fail: bool) -> None:
    generator = ImageGeneratorStub(result="" if not fail else "unused", fail=fail)
    result = asyncio.run(
        source_images_for_page(
            SPECS[:1],
            image_source=ImageSource.AI,
            industry="Bakery",
            company_name="Acme",
            image_generator=generator,
        )
    )

    assert result[0].src == PANEL_SENTINEL
    assert "No text or watermarks" in generator.prompts[0]


def test_pexels_source_appends_industry_and_preserves_credit() -> None:
    search = ImageSearchStub(("https://images.example/photo", "Ada"))
    result = asyncio.run(
        source_images_for_page(
            SPECS[:1],
            image_source=ImageSource.PEXELS,
            industry="Bakery",
            company_name="Acme",
            image_search=search,
        )
    )

    assert result[0].credit == "Ada"
    assert search.queries == ["Bakery counter Bakery"]


@pytest.mark.parametrize(
    ("source", "search"),
    [
        (ImageSource.PLACEHOLDER, None),
        (ImageSource.UPLOADED, None),
        (ImageSource.AI, None),
        (ImageSource.PEXELS, ImageSearchStub(fail=True)),
    ],
)
def test_unavailable_sources_fall_back_to_panel(
    source: ImageSource, search: ImageSearchStub | None
) -> None:
    result = asyncio.run(
        source_images_for_page(
            SPECS[:1],
            image_source=source,
            industry="Bakery",
            company_name="Acme",
            image_search=search,
        )
    )
    assert result[0].src == PANEL_SENTINEL
    assert is_real_image(result[0].src) is False
    assert is_real_image("https://example.com") is True


def test_render_image_catalog_handles_empty_panel_and_tokenized_image() -> None:
    assert render_image_catalog([]).startswith("No images assigned")
    registry = ImageRegistry()
    catalog = render_image_catalog(
        [
            SourcedImage(section="Hero", desc="Photo", src=PANEL_SENTINEL, alt="Photo"),
            SourcedImage(
                section="Team",
                desc="Team",
                src="data:image/png;base64,YWJj",
                alt="Team",
            ),
        ],
        registry,
    )

    assert "NO image available" in catalog
    assert "__IMG_REF_1__" in catalog
    assert "use each EXACTLY ONCE" in catalog
