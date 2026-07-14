"""Provider boundaries used by profile extraction."""

from typing import Protocol

from launchkit.profiles.models import ProfileFieldExtraction


class ProfileFieldExtractor(Protocol):
    async def extract_profile_fields(self, text: str) -> ProfileFieldExtraction:
        """Extract source-backed intake fields from document text."""


class ProfileImageLabeler(Protocol):
    async def label_image(self, data_url: str) -> str:
        """Return a short placement label for one uploaded image."""


class ProfileVisualFieldExtractor(Protocol):
    async def extract_profile_image_fields(self, data_url: str) -> ProfileFieldExtraction:
        """Extract source-backed intake fields from a profile image."""
