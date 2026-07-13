"""Offline tests for profile document parsing and extraction coordination."""

import asyncio
import zipfile
from io import BytesIO

import docx
import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from launchkit.intake.models import OnboardingFormPatch
from launchkit.profiles.extraction import (
    EMPTY_TEXT_WARNING,
    PDF_IMAGE_WARNING,
    PROFILE_TEXT_LIMIT,
    ProfileExtractionService,
)
from launchkit.profiles.models import ProfileDesignHints, ProfileFieldExtraction
from launchkit.profiles.parsing import (
    MAX_IMAGE_BYTES,
    UnsupportedProfileTypeError,
    extract_docx_images,
    extract_profile_text,
    profile_extension,
)


class FieldExtractorStub:
    def __init__(self) -> None:
        self.text = ""

    async def extract_profile_fields(self, text: str) -> ProfileFieldExtraction:
        self.text = text
        return ProfileFieldExtraction(
            fields=OnboardingFormPatch(company_name="Acme"),
            design_hints=ProfileDesignHints(tagline="Build clearly"),
        )


class ImageLabelerStub:
    def __init__(self, *, fail: bool = False, label: str = "company logo.") -> None:
        self.fail = fail
        self.label = label
        self.urls: list[str] = []

    async def label_image(self, data_url: str) -> str:
        self.urls.append(data_url)
        if self.fail:
            raise RuntimeError("provider unavailable")
        return self.label


def make_docx(text: str, images: list[tuple[str, bytes]] | None = None) -> bytes:
    buffer = BytesIO()
    document = docx.Document()
    document.add_paragraph(text)
    document.save(buffer)
    if images:
        with zipfile.ZipFile(buffer, mode="a") as archive:
            for name, content in images:
                archive.writestr(f"word/media/{name}", content)
    return buffer.getvalue()


def make_text_pdf(text: str) -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)  # noqa: SLF001
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
    )
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)  # noqa: SLF001
    writer.write(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("filename", "expected"),
    [("PROFILE.PDF", "pdf"), ("profile", ""), ("archive.profile.docx", "docx")],
)
def test_profile_extension(filename: str, expected: str) -> None:
    assert profile_extension(filename) == expected


def test_extract_profile_text_supports_plain_docx_and_pdf() -> None:
    assert extract_profile_text(b"hello\xff", "profile.txt") == "hello\ufffd"
    assert extract_profile_text(b"# Brief", "profile.md") == "# Brief"
    assert extract_profile_text(make_docx("Company profile"), "profile.docx") == "Company profile"
    assert extract_profile_text(make_text_pdf("PDF profile"), "profile.pdf") == "PDF profile"


def test_extract_profile_text_rejects_unknown_or_missing_extension() -> None:
    with pytest.raises(UnsupportedProfileTypeError, match=r"\.csv"):
        extract_profile_text(b"data", "profile.csv")
    with pytest.raises(UnsupportedProfileTypeError, match="file type"):
        extract_profile_text(b"data", "profile")


def test_extract_docx_images_limits_candidates_before_size_filter() -> None:
    images = [("oversized.jpg", b"x" * (MAX_IMAGE_BYTES + 1))]
    images.extend((f"image-{index}.png", bytes([index])) for index in range(1, 9))

    extracted = extract_docx_images(make_docx("Profile", images))

    assert [image.filename for image in extracted] == [
        f"image-{index}.png" for index in range(1, 8)
    ]
    assert all(image.mime_type == "image/png" for image in extracted)


def test_profile_service_extracts_fields_labels_and_data_urls() -> None:
    fields = FieldExtractorStub()
    labels = ImageLabelerStub()
    service = ProfileExtractionService(fields, labels)
    content = make_docx("A" * (PROFILE_TEXT_LIMIT + 100), [("logo.jpg", b"image")])

    result = asyncio.run(service.extract(content, "company.docx"))

    assert len(fields.text) == PROFILE_TEXT_LIMIT
    assert result.fields.company_name == "Acme"
    assert result.design_hints.tagline == "Build clearly"
    assert result.images[0].label == "company logo"
    assert result.images[0].data_url == "data:image/jpeg;base64,aW1hZ2U="
    assert labels.urls == [result.images[0].data_url]
    assert result.warnings == []


def test_profile_service_skips_field_call_for_empty_pdf_and_warns() -> None:
    fields = FieldExtractorStub()
    service = ProfileExtractionService(fields, ImageLabelerStub())
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    content = BytesIO()
    writer.write(content)

    result = asyncio.run(service.extract(content.getvalue(), "empty.pdf"))

    assert fields.text == ""
    assert result.fields.model_dump(exclude_none=True) == {}
    assert result.warnings == [EMPTY_TEXT_WARNING, PDF_IMAGE_WARNING]


@pytest.mark.parametrize(("fail", "label"), [(True, "ignored"), (False, "")])
def test_profile_service_uses_photo_when_labeling_fails_or_is_empty(fail: bool, label: str) -> None:
    service = ProfileExtractionService(
        FieldExtractorStub(), ImageLabelerStub(fail=fail, label=label)
    )
    content = make_docx("Profile", [("photo.png", b"image")])

    result = asyncio.run(service.extract(content, "profile.docx"))

    assert result.images[0].label == "photo"
