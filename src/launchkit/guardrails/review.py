"""Model-assisted submission review with deterministic fail-closed parsing."""

import json
from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from launchkit.generation.contracts import TextGenerator
from launchkit.generation.legacy_prompts import GUARDRAIL_SYSTEM_PROMPT
from launchkit.guardrails.models import GuardrailDecision, GuardrailResult

UNPARSEABLE_RESULT = GuardrailResult(
    decision=GuardrailDecision.REJECT,
    reason="We couldn't automatically verify this submission. Please try again.",
    categories=["unparseable_guardrail_response"],
)


class GuardrailReviewService:
    """Review raw intake while preserving legacy fail-closed behavior."""

    def __init__(self, generator: TextGenerator) -> None:
        self._generator = generator

    async def review(self, raw: Mapping[str, Any]) -> GuardrailResult:
        submitted = json.dumps(dict(raw), ensure_ascii=False, indent=2)
        response = await self._generator.generate_text(
            f"Company submission to review:\n\n{submitted}",
            system=GUARDRAIL_SYSTEM_PROMPT,
            max_tokens=400,
        )
        return parse_guardrail_result(response)


def parse_guardrail_result(response: str) -> GuardrailResult:
    """Parse the first-to-last JSON object or return the fixed rejection."""

    start, end = response.find("{"), response.rfind("}")
    if start == -1 or end == -1:
        return UNPARSEABLE_RESULT.model_copy(deep=True)
    try:
        payload = json.loads(response[start : end + 1])
        if not isinstance(payload, Mapping):
            return UNPARSEABLE_RESULT.model_copy(deep=True)
        return GuardrailResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError):
        return UNPARSEABLE_RESULT.model_copy(deep=True)
