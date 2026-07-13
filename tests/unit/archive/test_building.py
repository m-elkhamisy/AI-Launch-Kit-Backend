"""Generated HTML archive tests."""

import zipfile
from io import BytesIO

import pytest

from launchkit.archive import build_site_zip, html_download_payload
from launchkit.core.exceptions import DomainError
from launchkit.generation.models import BuiltPage


def page(name: str, slug: str, filename: str) -> BuiltPage:
    return BuiltPage(name=name, slug=slug, filename=filename, html=f"<h1>{name}</h1>")


def test_build_site_zip_contains_safe_page_filenames() -> None:
    result = build_site_zip(
        [page("Home", "index", "index.html"), page("About", "about", "nested/about.html")],
        "Acme & Co",
    )
    with zipfile.ZipFile(BytesIO(result.content)) as archive:
        assert archive.namelist() == ["index.html", "about.html"]
        assert archive.read("about.html") == b"<h1>About</h1>"
    assert result.filename == "acme-co-website.zip"


def test_archive_rejects_empty_pages_and_builds_single_html() -> None:
    with pytest.raises(DomainError):
        build_site_zip([], "Acme")
    result = html_download_payload(page("Home", "index", "nested/index.html"))
    assert result.filename == "index.html"
    assert result.content == b"<h1>Home</h1>"
