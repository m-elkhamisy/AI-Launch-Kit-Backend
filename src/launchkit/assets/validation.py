"""Strict validation for the profile formats advertised by the wizard."""

import re
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

import docx
import pptx
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader

from launchkit.core.exceptions import DomainError

MIME_TYPES = {
    "pdf": {"application/pdf"},
    "docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    "pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    "txt": {"text/plain"},
    "md": {"text/markdown", "text/plain"},
    "png": {"image/png"},
    "jpg": {"image/jpeg"},
    "jpeg": {"image/jpeg"},
    "svg": {"image/svg+xml"},
}

LOGO_EXTENSIONS = frozenset({"png", "jpg", "jpeg", "svg"})
DOCUMENT_EXTENSIONS = frozenset({"pdf", "docx", "pptx", "txt", "md", "png", "jpg", "jpeg"})
BRAND_ASSET_MAX_BYTES = 1_572_864  # 1.5 MB


class UploadValidationError(DomainError):
    """Raised when an upload does not match the accepted profile contract."""


class UploadTooLargeError(UploadValidationError):
    """Raised when an upload exceeds the configured byte limit."""


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    filename: str
    content_type: str
    extension: str
    content: bytes


def _assert_readable(extension: str, content: bytes) -> None:
    try:
        if extension == "pdf":
            PdfReader(BytesIO(content))
        elif extension == "docx":
            docx.Document(BytesIO(content))
        elif extension == "pptx":
            pptx.Presentation(BytesIO(content))
        elif extension in {"png", "jpg", "jpeg"}:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        elif extension == "svg":
            text = content.decode("utf-8", errors="ignore").lstrip().lower()
            if "<svg" not in text:
                raise UploadValidationError("The SVG logo is malformed or unreadable.")
            if "<script" in text or "javascript:" in text:
                raise UploadValidationError("The SVG logo contains disallowed content.")
        elif b"\x00" in content:
            raise UploadValidationError("The text profile contains binary data.")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, UnidentifiedImageError) as exc:
        raise UploadValidationError("The uploaded profile is malformed or unreadable.") from exc


def validate_profile_upload(
    filename: str, content_type: str, content: bytes, *, max_bytes: int
) -> ValidatedUpload:
    safe_name = safe_filename(filename)
    extension = safe_name.rsplit(".", maxsplit=1)[-1].lower() if "." in safe_name else ""
    if not safe_name or extension not in MIME_TYPES or extension == "svg":
        raise UploadValidationError("Upload a PDF, DOCX, PPTX, TXT, MD, PNG, or JPG file.")
    if content_type.lower().split(";", maxsplit=1)[0] not in MIME_TYPES[extension]:
        raise UploadValidationError("The uploaded file type does not match its extension.")
    if not content:
        raise UploadValidationError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise UploadTooLargeError(
            f"The uploaded file exceeds the {max_bytes // (1024 * 1024)} MB limit."
        )
    _assert_readable(extension, content)
    return ValidatedUpload(safe_name, content_type, extension, content)


def validate_brand_upload(
    filename: str,
    content_type: str,
    content: bytes,
    *,
    kind: str,
    max_bytes: int = BRAND_ASSET_MAX_BYTES,
) -> ValidatedUpload:
    """Validate a logo or supporting brand document for the Business step."""

    allowed = LOGO_EXTENSIONS if kind == "logo" else DOCUMENT_EXTENSIONS
    safe_name = safe_filename(filename)
    extension = safe_name.rsplit(".", maxsplit=1)[-1].lower() if "." in safe_name else ""
    if not safe_name or extension not in allowed:
        if kind == "logo":
            raise UploadValidationError("Upload a PNG, SVG, or JPG logo.")
        raise UploadValidationError("Upload a PDF, DOCX, PPTX, TXT, MD, PNG, or JPG file.")
    mime = content_type.lower().split(";", maxsplit=1)[0]
    if mime not in MIME_TYPES[extension]:
        # Browsers often omit accurate SVG MIME; accept empty or octet-stream for SVG.
        if not (extension == "svg" and mime in {"", "application/octet-stream"}):
            raise UploadValidationError("The uploaded file type does not match its extension.")
    if not content:
        raise UploadValidationError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise UploadTooLargeError("Each brand file must be 1.5 MB or smaller.")
    _assert_readable(extension, content)
    normalized_type = (
        "image/svg+xml" if extension == "svg" else (content_type or next(iter(MIME_TYPES[extension])))
    )
    return ValidatedUpload(safe_name, normalized_type, extension, content)


def safe_filename(value: str, fallback: str = "file") -> str:
    basename = PurePosixPath(value.replace("\\", "/")).name.strip()
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "_", basename).strip(" .")
    return (normalized or fallback)[:120]
