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

PROFILE_TEXT_LIMIT = 28_000
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
        return await self.extract_many([(content, filename)])

    async def extract_many(self, files: list[tuple[bytes, str]]) -> ProfileExtractionResult:
        """Extract one website brief from one or more brand documents (single LLM call)."""

        if not files:
            return ProfileExtractionResult(
                fields=OnboardingFormPatch(),
                design_hints=ProfileDesignHints(),
                images=[],
                source_filename="",
                warnings=[EMPTY_TEXT_WARNING],
            )

        warnings: list[str] = []
        text_parts: list[str] = []
        images: list[ExtractedImage] = []
        names: list[str] = []
        sole_image: tuple[bytes, str] | None = None

        for content, filename in files:
            names.append(filename)
            extension = profile_extension(filename)
            is_image = extension in {"png", "jpg", "jpeg"}
            if extension == "pdf":
                warnings.append(f"{filename}: {PDF_IMAGE_WARNING}")

            if is_image:
                if len(files) == 1:
                    sole_image = (content, filename)
                continue

            text = await asyncio.to_thread(extract_profile_text, content, filename)
            if text.strip():
                text_parts.append(f"### File: {filename}\n{text.strip()}")
            else:
                warnings.append(f"{filename}: {EMPTY_TEXT_WARNING}")

            if extension == "docx":
                raw_images = await asyncio.to_thread(extract_docx_images, content)
            elif extension == "pptx":
                raw_images = await asyncio.to_thread(extract_pptx_images, content)
            else:
                raw_images = []
            labeled = await asyncio.gather(*(self._to_extracted_image(image) for image in raw_images))
            images.extend(labeled)

        source_filename = ", ".join(names)

        if sole_image is not None and not text_parts:
            content, filename = sole_image
            data_url = self._data_url(
                content,
                f"image/{'jpeg' if profile_extension(filename) in {'jpg', 'jpeg'} else profile_extension(filename)}",
            )
            extraction = await self._extract_visual_fields(data_url)
            try:
                label = (
                    (await self._image_labeler.label_image(data_url)).strip().removesuffix(".")
                )
            except Exception:
                label = "profile image"
            return ProfileExtractionResult(
                fields=extraction.fields,
                design_hints=extraction.design_hints,
                images=[
                    ExtractedImage(
                        filename=filename,
                        label=label or "profile image",
                        data_url=data_url,
                    )
                ],
                source_filename=source_filename,
                warnings=warnings,
            )

        combined = "\n\n".join(text_parts)[:PROFILE_TEXT_LIMIT]
        if not combined.strip():
            warnings.append(EMPTY_TEXT_WARNING)
        extraction = await self._extract_fields(combined)
        return ProfileExtractionResult(
            fields=extraction.fields,
            design_hints=extraction.design_hints,
            images=images,
            source_filename=source_filename,
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
