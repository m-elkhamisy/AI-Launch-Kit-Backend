"""Profile extraction service independent of HTTP and provider implementations."""

import asyncio
import base64

from launchkit.intake.models import OnboardingFormPatch
from launchkit.profiles.contracts import (
    ProfileFieldExtractor,
    ProfileImageLabeler,
    ProfileVisualFieldExtractor,
)
from launchkit.profiles.models import (
    ExtractedImage,
    ProfileDesignHints,
    ProfileExtractionResult,
    ProfileFieldExtraction,
)
from launchkit.profiles.parsing import (
    RawProfileImage,
    extract_docx_images,
    extract_pptx_images,
    extract_profile_text,
    profile_extension,
)

PROFILE_TEXT_LIMIT = 12_000
EMPTY_TEXT_WARNING = "Couldn't find any readable text in this file - the form wasn't prefilled."
PDF_IMAGE_WARNING = (
    "Photo extraction from PDFs isn't supported yet - text was extracted, but embedded photos "
    "weren't. Upload a DOCX instead if you want your own photos pulled in, or pick "
    "AI-generated/stock photos."
)


class ProfileExtractionService:
    """Extract profile fields and DOCX images using injected provider capabilities."""

    def __init__(
        self,
        field_extractor: ProfileFieldExtractor,
        image_labeler: ProfileImageLabeler,
        visual_field_extractor: ProfileVisualFieldExtractor | None = None,
    ) -> None:
        self._field_extractor = field_extractor
        self._image_labeler = image_labeler
        self._visual_field_extractor = visual_field_extractor

    async def extract(self, content: bytes, filename: str) -> ProfileExtractionResult:
        extension = profile_extension(filename)
        is_image = extension in {"png", "jpg", "jpeg"}
        text = "" if is_image else await asyncio.to_thread(extract_profile_text, content, filename)
        warnings: list[str] = []
        if not is_image and not text.strip():
            warnings.append(EMPTY_TEXT_WARNING)
        if extension == "pdf":
            warnings.append(PDF_IMAGE_WARNING)

        source_data_url = (
            self._data_url(
                content, f"image/{'jpeg' if extension in {'jpg', 'jpeg'} else extension}"
            )
            if is_image
            else None
        )
        fields_task = asyncio.create_task(
            self._extract_visual_fields(source_data_url)
            if source_data_url is not None
            else self._extract_fields(text)
        )
        if extension == "docx":
            raw_images = await asyncio.to_thread(extract_docx_images, content)
        elif extension == "pptx":
            raw_images = await asyncio.to_thread(extract_pptx_images, content)
        else:
            raw_images = []
        extraction = await fields_task
        images = await asyncio.gather(*(self._to_extracted_image(image) for image in raw_images))
        if source_data_url is not None:
            try:
                label = (
                    (await self._image_labeler.label_image(source_data_url))
                    .strip()
                    .removesuffix(".")
                )
            except Exception:
                label = "profile image"
            images = [
                ExtractedImage(
                    filename=filename, label=label or "profile image", data_url=source_data_url
                )
            ]

        return ProfileExtractionResult(
            fields=extraction.fields,
            design_hints=extraction.design_hints,
            images=list(images),
            source_filename=filename,
            warnings=warnings,
        )

    async def _extract_fields(self, text: str) -> ProfileFieldExtraction:
        if not text.strip():
            return ProfileFieldExtraction(
                fields=OnboardingFormPatch(),
                design_hints=ProfileDesignHints(),
            )
        return await self._field_extractor.extract_profile_fields(text[:PROFILE_TEXT_LIMIT])

    async def _extract_visual_fields(self, data_url: str) -> ProfileFieldExtraction:
        if self._visual_field_extractor is None:
            return ProfileFieldExtraction(
                fields=OnboardingFormPatch(), design_hints=ProfileDesignHints()
            )
        return await self._visual_field_extractor.extract_profile_image_fields(data_url)

    async def _to_extracted_image(self, image: RawProfileImage) -> ExtractedImage:
        data_url = self._data_url(image.content, image.mime_type)
        try:
            label = (await self._image_labeler.label_image(data_url)).strip().removesuffix(".")
        except Exception:
            label = "photo"
        return ExtractedImage(
            filename=image.filename,
            label=label or "photo",
            data_url=data_url,
        )

    @staticmethod
    def _data_url(content: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
