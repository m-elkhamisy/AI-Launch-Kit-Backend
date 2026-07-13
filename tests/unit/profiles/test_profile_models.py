from launchkit.profiles import ProfileExtractionResult, ProfileFieldExtraction, SourcedImage


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


def test_sourced_image_preserves_optional_credit() -> None:
    image = SourcedImage(
        section="Hero", desc="Office", src="data:image/png;base64,abc", alt="Office"
    )

    assert image.credit is None


def test_profile_field_extraction_uses_camel_case_aliases() -> None:
    extraction = ProfileFieldExtraction.model_validate(
        {"fields": {"companyName": "Acme"}, "designHints": {"cta": "Call us"}}
    )

    assert extraction.model_dump(by_alias=True, exclude_none=True) == {
        "fields": {"companyName": "Acme"},
        "designHints": {"cta": "Call us"},
    }
