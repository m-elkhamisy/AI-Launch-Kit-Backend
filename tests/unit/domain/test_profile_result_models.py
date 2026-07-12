from launchkit.domain.models import (
    DeploymentResult,
    GuardrailDecision,
    GuardrailResult,
    LegacyCompany,
    ProfileExtractionResult,
    SourcedImage,
    StoredSubmission,
)


def _legacy_company() -> LegacyCompany:
    return LegacyCompany(
        name="Acme",
        industry="Tech",
        tagline="",
        description="Tools",
        services="Automation",
        audience="Teams",
        tone="Direct",
        location="Dubai",
        website="",
        contact_email="",
        contact_phone="",
        colorway="",
        animation_level="",
    )


def test_profile_result_accepts_partial_fields() -> None:
    result = ProfileExtractionResult.model_validate(
        {
            "fields": {"companyName": "Acme"},
            "designHints": {"tagline": "Move faster"},
            "images": [],
            "sourceFilename": "profile.docx",
            "warnings": [],
        }
    )

    payload = result.model_dump(by_alias=True, mode="json", exclude_none=True)
    assert payload["fields"] == {"companyName": "Acme"}
    assert payload["sourceFilename"] == "profile.docx"


def test_supporting_results_preserve_reference_shapes() -> None:
    guardrail_a = GuardrailResult(decision=GuardrailDecision.ACCEPT)
    guardrail_b = GuardrailResult(decision=GuardrailDecision.REJECT)
    guardrail_a.categories.append("reviewed")
    stored = StoredSubmission(id="company_1", raw={"name": "Acme"}, normalized=_legacy_company())
    deployment = DeploymentResult(
        chat_id="chat_1",
        project_id="project_1",
        deployment_id=None,
        live_url=None,
        claim_url="https://vercel.com/claim-deployment?code=abc",
        note="Transfer the project.",
    )
    image = SourcedImage(
        section="Hero", desc="Office", src="data:image/png;base64,abc", alt="Office"
    )

    assert guardrail_b.categories == []
    assert stored.normalized.name == "Acme"
    assert deployment.model_dump(by_alias=True, mode="json")["claimExpires"] == "24 hours"
    assert image.credit is None
