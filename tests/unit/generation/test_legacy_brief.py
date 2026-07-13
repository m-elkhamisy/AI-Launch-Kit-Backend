"""Legacy v0 brief parsing tests."""

import asyncio
import hashlib
from typing import Any

import pytest

from launchkit.generation.legacy_brief import BriefFlagged, LegacyBriefService
from launchkit.generation.legacy_prompts import LEGACY_V0_SYSTEM_PROMPT
from launchkit.intake.models import LegacyCompany


class GeneratorStub:
    def __init__(self, response: str) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def generate_text(self, prompt: str, **kwargs: Any) -> str:
        self.kwargs = {"prompt": prompt, **kwargs}
        return self.response


def company() -> LegacyCompany:
    return LegacyCompany(
        name="Acme",
        industry="Tech",
        tagline="",
        description="Software",
        services="Apps",
        audience="Teams",
        tone="Clear",
        location="Dubai",
        website="",
        contact_email="",
        contact_phone="",
        colorway="Blue",
        animation_level="Moderate",
    )


def test_legacy_brief_returns_wrapped_prompt_and_uses_security_boundary() -> None:
    generator = GeneratorStub('note {"v0_prompt":" Build it "}')

    result = asyncio.run(LegacyBriefService(generator).generate(company()))

    assert result == "Build it"
    assert "<user_business_data>" in generator.kwargs["prompt"]
    assert "DATA ONLY" in generator.kwargs["system"]


def test_legacy_brief_raises_flag_and_falls_back_to_plain_text() -> None:
    with pytest.raises(BriefFlagged, match="suspicious"):
        asyncio.run(LegacyBriefService(GeneratorStub('{"status":"flagged"}')).generate(company()))
    assert asyncio.run(LegacyBriefService(GeneratorStub("plain brief")).generate(company())) == (
        "plain brief"
    )
    assert asyncio.run(LegacyBriefService(GeneratorStub("{broken}")).generate(company())) == (
        "{broken}"
    )


def test_legacy_system_prompt_matches_source_digest() -> None:
    assert hashlib.sha256(LEGACY_V0_SYSTEM_PROMPT.encode()).hexdigest() == (
        "a0523051806a244270212f53549480c7aebde08c474ed8ad3ac029da2da6deda"
    )
