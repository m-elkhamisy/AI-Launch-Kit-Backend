"""Blocking parsers for supported profile document formats."""

import mimetypes
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

import docx
import pptx
from pypdf import PdfReader

from launchkit.core.exceptions import DomainError

MAX_IMAGES = 8
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class UnsupportedProfileTypeError(DomainError):
    """Raised when an uploaded profile is not a supported document type."""


@dataclass(frozen=True, slots=True)
class RawProfileImage:
    filename: str
    content: bytes
    mime_type: str


def profile_extension(filename: str) -> str:
    """Return the lowercase suffix without a leading dot."""

    return filename.rsplit(".", maxsplit=1)[-1].lower() if "." in filename else ""


def extract_profile_text(content: bytes, filename: str) -> str:
    """Extract readable text from PDF, DOCX, TXT, or Markdown bytes."""

    extension = profile_extension(filename)
    if extension == "pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
    if extension == "docx":
        document = docx.Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    if extension == "pptx":
        presentation = pptx.Presentation(BytesIO(content))
        lines: list[str] = []
        for slide in presentation.slides:
            for shape in slide.shapes:
                text = getattr(shape, "text", None)
                if isinstance(text, str) and text.strip():
                    lines.append(text)
        return "\n".join(lines)
    if extension in {"txt", "md"}:
        return content.decode("utf-8", errors="replace")
    suffix = f".{extension}" if extension else "."
    raise UnsupportedProfileTypeError(
        f'Unsupported file type "{suffix}" - upload a PDF, DOCX, PPTX, TXT, MD, PNG, or JPG file.'
    )


def extract_docx_images(content: bytes) -> list[RawProfileImage]:
    """Return up to eight size-limited images stored under ``word/media``."""

    images: list[RawProfileImage] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.startswith("word/media/")]
        for name in names[:MAX_IMAGES]:
            data = archive.read(name)
            if len(data) > MAX_IMAGE_BYTES:
                continue
            filename = PurePosixPath(name).name
            extension = PurePosixPath(filename).suffix.lower()
            mime_type = mimetypes.types_map.get(
                extension, f"image/{extension.lstrip('.') or 'png'}"
            )
            if extension == ".jpg":
                mime_type = "image/jpeg"
            images.append(RawProfileImage(filename, data, mime_type))
    return images


def extract_pptx_images(content: bytes) -> list[RawProfileImage]:
    """Return size-limited images stored in a PowerPoint package."""

    images: list[RawProfileImage] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.startswith("ppt/media/")]
        for name in names[:MAX_IMAGES]:
            data = archive.read(name)
            if len(data) > MAX_IMAGE_BYTES:
                continue
            filename = PurePosixPath(name).name
            extension = PurePosixPath(filename).suffix.lower()
            mime_type = mimetypes.types_map.get(
                extension, f"image/{extension.lstrip('.') or 'png'}"
            )
            if extension in {".jpg", ".jpeg"}:
                mime_type = "image/jpeg"
            images.append(RawProfileImage(filename, data, mime_type))
    return images
