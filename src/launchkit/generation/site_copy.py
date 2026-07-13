"""Best-effort extraction of copy already present in generated homepage HTML."""

from launchkit.generation.contracts import StructuredGenerator
from launchkit.generation.models import SiteCopy


class SiteCopyExtractor:
    def __init__(self, generator: StructuredGenerator) -> None:
        self._generator = generator

    async def extract(self, homepage_html: str) -> SiteCopy | None:
        prompt = f"""Read this HTML homepage and extract ONLY copy literally present in the
markup. Do not add or improve claims. Return ONLY valid JSON:
{{"headline":"","subheadline":"","sections":[{{"heading":"","body":""}}],"callToAction":""}}
Include at most 4 sections. Use an empty string when no clear value exists.

HTML:
{homepage_html[:12000]}"""
        try:
            payload = await self._generator.generate_json(prompt, max_tokens=1_200)
            return SiteCopy.model_validate(payload)
        except Exception:
            return None
