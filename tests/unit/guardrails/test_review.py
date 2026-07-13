"""Guardrail service and fail-closed parser tests."""

import asyncio
import hashlib
from typing import Any

import pytest

from launchkit.generation.legacy_prompts import GUARDRAIL_SYSTEM_PROMPT
from launchkit.guardrails import GuardrailDecision, GuardrailReviewService, parse_guardrail_result


class GeneratorStub:
    def __init__(self, response: str) -> None:
        self.response = response
        self.kwargs: dict[str, Any] = {}

    async def generate_text(self, prompt: str, **kwargs: Any) -> str:
        self.kwargs = {"prompt": prompt, **kwargs}
        return self.response


def test_guardrail_service_serializes_input_and_applies_defaults() -> None:
    generator = GeneratorStub('prefix {"decision":"accept"} suffix')

    result = asyncio.run(GuardrailReviewService(generator).review({"company": "Caf\u00e9"}))

    assert result.decision is GuardrailDecision.ACCEPT
    assert result.reason == ""
    assert result.categories == []
    assert "Caf\u00e9" in generator.kwargs["prompt"]
    assert generator.kwargs["max_tokens"] == 400


@pytest.mark.parametrize(
    "response",
    ["no json", "{broken}", "[]", '{"decision":"maybe"}', '{"decision":"accept","extra":1}'],
)
def test_guardrail_parser_fails_closed(response: str) -> None:
    result = parse_guardrail_result(response)

    assert result.decision is GuardrailDecision.REJECT
    assert result.categories == ["unparseable_guardrail_response"]


def test_guardrail_prompt_matches_source_digest() -> None:
    assert hashlib.sha256(GUARDRAIL_SYSTEM_PROMPT.encode()).hexdigest() == (
        "2652cd3b1b462d4cbfa6fa82c842dfa7ae3c5ab5121b4430e95fbae0596721de"
    )
