"""Legacy company-to-v0 brief generation preserved behind a typed service."""

import json
from collections.abc import Mapping

from launchkit.core.exceptions import DomainError
from launchkit.generation.contracts import TextGenerator
from launchkit.generation.legacy_prompts import LEGACY_V0_SYSTEM_PROMPT
from launchkit.generation.prompts.brief import build_legacy_brief_user_message
from launchkit.intake.models import LegacyCompany


class BriefFlagged(DomainError):
    """Raised when the legacy brief model flags likely prompt injection."""


class LegacyBriefService:
    """Generate the legacy v0 brief while keeping its policy isolated."""

    def __init__(self, generator: TextGenerator) -> None:
        self._generator = generator

    async def generate(self, company: LegacyCompany) -> str:
        response = (
            await self._generator.generate_text(
                build_legacy_brief_user_message(company),
                system=LEGACY_V0_SYSTEM_PROMPT,
                max_tokens=4_000,
            )
        ).strip()
        if not response:
            return response
        parsed = _parse_object(response)
        if parsed is not None and parsed.get("status") == "flagged":
            raise BriefFlagged(str(parsed.get("reason") or "suspicious input"))
        if parsed is not None:
            prompt = parsed.get("v0_prompt")
            if isinstance(prompt, str) and prompt.strip():
                return prompt.strip()
        return response


def _parse_object(value: str) -> Mapping[str, object] | None:
    start, end = value.find("{"), value.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        payload = json.loads(value[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, Mapping) else None
