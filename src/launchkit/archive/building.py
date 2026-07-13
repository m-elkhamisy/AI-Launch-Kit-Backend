"""Pure construction of downloadable HTML and ZIP payloads."""

import zipfile
from collections.abc import Sequence
from io import BytesIO
from pathlib import PurePosixPath

from launchkit.core.exceptions import DomainError
from launchkit.generation.models import ArchiveDownload, BuiltPage
from launchkit.planning.normalization import slugify


def build_site_zip(pages: Sequence[BuiltPage], company_name: str) -> ArchiveDownload:
    """Create an in-memory ZIP containing each generated HTML page."""

    if not pages:
        raise DomainError("Cannot create a site archive without generated pages")
    output = BytesIO()
    with zipfile.ZipFile(output, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for page in pages:
            filename = PurePosixPath(page.filename or f"{page.slug}.html").name
            archive.writestr(filename, page.html)
    return ArchiveDownload(
        content=output.getvalue(),
        filename=f"{slugify(company_name or 'website')}-website.zip",
    )


def html_download_payload(page: BuiltPage) -> ArchiveDownload:
    """Return one generated page as a downloadable HTML payload."""

    filename = PurePosixPath(page.filename or f"{page.slug}.html").name
    return ArchiveDownload(content=page.html.encode("utf-8"), filename=filename)
