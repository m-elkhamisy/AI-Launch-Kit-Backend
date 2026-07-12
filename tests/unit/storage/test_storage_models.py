from launchkit.intake import LegacyCompany
from launchkit.storage import StorageMetadata, StoredSubmission


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


def test_stored_submission_preserves_legacy_shape() -> None:
    metadata = StorageMetadata(id="company_1")
    stored = StoredSubmission(
        id=metadata.id,
        raw={"name": "Acme"},
        normalized=_legacy_company(),
    )

    assert stored.normalized.name == "Acme"
    assert stored.model_dump()["id"] == "company_1"
