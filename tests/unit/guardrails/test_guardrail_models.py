from launchkit.guardrails import GuardrailDecision, GuardrailResult


def test_guardrail_defaults_are_isolated() -> None:
    accepted = GuardrailResult(decision=GuardrailDecision.ACCEPT)
    rejected = GuardrailResult(decision=GuardrailDecision.REJECT)

    accepted.categories.append("reviewed")

    assert accepted.reason == ""
    assert rejected.categories == []
