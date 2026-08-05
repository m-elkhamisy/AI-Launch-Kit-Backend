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

    async def extract_from_text(self, text: str, source: str) -> ProfileExtractionResult:
        """Extract a website brief from already-readable text (e.g. a scraped web page)."""

        return await self.extract_many(
            [],
            website_text=text,
            website_url=source,
        )

    async def extract_many(
        self,
        files: list[tuple[bytes, str]] | None = None,
        *,
        website_text: str | None = None,
        website_url: str | None = None,
    ) -> ProfileExtractionResult:
        """Extract one brief from an optional website scrape first, then brand documents.

        Website text is always ordered ahead of documents so discovery prioritises the live site.
        """

        files = list(files or [])
        warnings: list[str] = []
        text_parts: list[str] = []
        images: list[ExtractedImage] = []
        names: list[str] = []
        sole_image: tuple[bytes, str] | None = None

        # 1) Scraped website first (when present).
        if website_text and website_text.strip():
            label = (website_url or "website").strip() or "website"
            names.append(label)
            text_parts.append(f"### Website: {label}\n{website_text.strip()}")
        elif website_url:
            warnings.append(f"{website_url}: {EMPTY_TEXT_WARNING}")

        # 2) Brand documents after the website.
        for content, filename in files:
            names.append(filename)
            extension = profile_extension(filename)
            is_image = extension in {"png", "jpg", "jpeg"}
            if extension == "pdf":
                warnings.append(f"{filename}: {PDF_IMAGE_WARNING}")

            if is_image:
                if len(files) == 1 and not text_parts:
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

        if not files and not text_parts:
            warnings.append(EMPTY_TEXT_WARNING)
            return ProfileExtractionResult(
                fields=OnboardingFormPatch(),
                design_hints=ProfileDesignHints(),
                images=[],
                source_filename=source_filename,
                warnings=warnings,
            )

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

        combined = self._combine_source_texts(text_parts)
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

    @staticmethod
    def _combine_source_texts(text_parts: list[str]) -> str:
        """Build one LLM context: website first (always kept in budget), then documents."""

        if not text_parts:
            return ""
        website_parts = [part for part in text_parts if part.startswith("### Website:")]
        document_parts = [part for part in text_parts if not part.startswith("### Website:")]
        if website_parts and document_parts:
            # Half the budget each so large menus never wipe the scraped site (or vice versa).
            website_budget = PROFILE_TEXT_LIMIT // 2
            document_budget = PROFILE_TEXT_LIMIT - website_budget
            website_block = "\n\n".join(website_parts)[:website_budget]
            document_block = "\n\n".join(document_parts)[:document_budget]
            return f"{website_block}\n\n{document_block}"
        return "\n\n".join(text_parts)[:PROFILE_TEXT_LIMIT]

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
