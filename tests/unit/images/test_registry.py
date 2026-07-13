"""Image data-URI registry tests."""

from launchkit.images.registry import ImageRegistry


def test_registry_reuses_tokens_and_restores_sources() -> None:
    registry = ImageRegistry()
    first = "data:image/png;base64,YWJj"
    second = "data:image/jpeg;base64,ZGVm"
    original = f'<img src="{first}"><img src="{first}"><img src="{second}">'

    compressed = registry.compress(original)

    assert compressed.count("__IMG_REF_1__") == 2
    assert compressed.count("__IMG_REF_2__") == 1
    assert registry.resolve(compressed) == original


def test_registry_is_noop_for_empty_external_or_unknown_tokens() -> None:
    registry = ImageRegistry()

    assert registry.compress("") == ""
    assert registry.resolve("") == ""
    assert registry.compress("https://example.com/a.jpg") == "https://example.com/a.jpg"
    assert registry.resolve("__IMG_REF_99__") == "__IMG_REF_99__"
