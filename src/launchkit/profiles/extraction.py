"""Profile extraction service independent of HTTP and provider implementations."""

import asyncio
import base64

from launchkit.intake.models import OnboardingFormPatch
from launchkit.profiles.contracts import ProfileFieldExtractor, ProfileImageLabeler
from launchkit.profiles.models import (
    ExtractedImage,
    ProfileDesignHints,
    ProfileExtractionResult,
    ProfileFieldExtraction,
)
from launchkit.profiles.parsing import (
    RawProfileImage,
    extract_docx_images,
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
    ) -> None:
        self._field_extractor = field_extractor
        self._image_labeler = image_labeler

    async def extract(self, content: bytes, filename: str) -> ProfileExtractionResult:
        text = await asyncio.to_thread(extract_profile_text, content, filename)
        extension = profile_extension(filename)
        warnings: list[str] = []
        if not text.strip():
            warnings.append(EMPTY_TEXT_WARNING)
        if extension == "pdf":
            warnings.append(PDF_IMAGE_WARNING)

        fields_task = asyncio.create_task(self._extract_fields(text))
        raw_images = (
            await asyncio.to_thread(extract_docx_images, content) if extension == "docx" else []
        )
        extraction = await fields_task
        images = await asyncio.gather(*(self._to_extracted_image(image) for image in raw_images))

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

    async def _to_extracted_image(self, image: RawProfileImage) -> ExtractedImage:
        encoded = base64.b64encode(image.content).decode("ascii")
        data_url = f"data:{image.mime_type};base64,{encoded}"
        try:
            label = (await self._image_labeler.label_image(data_url)).strip().removesuffix(".")
        except Exception:
            label = "photo"
        return ExtractedImage(
            filename=image.filename,
            label=label or "photo",
            data_url=data_url,
        )
