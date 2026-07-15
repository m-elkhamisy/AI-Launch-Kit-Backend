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
}


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


def validate_profile_upload(
    filename: str, content_type: str, content: bytes, *, max_bytes: int
) -> ValidatedUpload:
    safe_name = safe_filename(filename)
    extension = safe_name.rsplit(".", maxsplit=1)[-1].lower() if "." in safe_name else ""
    if not safe_name or extension not in MIME_TYPES:
        raise UploadValidationError("Upload a PDF, DOCX, PPTX, TXT, MD, PNG, or JPG file.")
    if content_type.lower().split(";", maxsplit=1)[0] not in MIME_TYPES[extension]:
        raise UploadValidationError("The uploaded file type does not match its extension.")
    if not content:
        raise UploadValidationError("The uploaded file is empty.")
    if len(content) > max_bytes:
        raise UploadTooLargeError(
            f"The uploaded file exceeds the {max_bytes // (1024 * 1024)} MB limit."
        )
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
        elif b"\x00" in content:
            raise UploadValidationError("The text profile contains binary data.")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, UnidentifiedImageError) as exc:
        raise UploadValidationError("The uploaded profile is malformed or unreadable.") from exc
    return ValidatedUpload(safe_name, content_type, extension, content)


def safe_filename(value: str, fallback: str = "file") -> str:
    basename = PurePosixPath(value.replace("\\", "/")).name.strip()
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "_", basename).strip(" .")
    return (normalized or fallback)[:120]
