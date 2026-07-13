"""Tests for Vercel inline-file conversion."""

import zipfile
from io import BytesIO

import pytest

from launchkit.core.exceptions import DomainError
from launchkit.deployment.archive import collect_deployment_files


def make_zip(files: dict[str, bytes]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("folder/", b"")
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def test_collect_deployment_files_decodes_text_and_base64_binary() -> None:
    files = collect_deployment_files(
        make_zip(
            {
                "index.html": b"<html />",
                "image.bin": b"\xff\x00",
                ".DS_Store": b"ignored",
                "__MACOSX/meta": b"ignored",
            }
        )
    )

    assert [file.file for file in files] == ["index.html", "image.bin"]
    assert files[0].data == "<html />"
    assert files[0].encoding is None
    assert files[1].data == "/wA="
    assert files[1].encoding == "base64"


@pytest.mark.parametrize("content", [b"bad", make_zip({".DS_Store": b"ignored"})])
def test_collect_deployment_files_rejects_bad_or_empty_archive(content: bytes) -> None:
    with pytest.raises(DomainError):
        collect_deployment_files(content)
