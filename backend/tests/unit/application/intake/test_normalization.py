import json
from pathlib import Path
from typing import Any

import pytest

from launchkit.application.intake.normalization import (
    flatten_submission,
    missing_required_fields,
    normalize_company,
)
from launchkit.domain.models import DesignPreferences, OnboardingField, OnboardingForm

FIXTURES = Path(__file__).parents[3] / "fixtures"


def _load_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_json("legacy_normalization_cases.json"))
def test_normalization_matches_legacy_characterization(case: dict[str, Any]) -> None:
    normalized = normalize_company(case["input"])

    assert normalized.model_dump() == case["expected"], case["name"]


def test_flatten_submission_drops_malformed_raw_column() -> None:
    assert flatten_submission({"raw": "{broken", "name": "Acme"}) == {"name": "Acme"}


def test_haseeb_fixtures_validate_with_no_missing_fields() -> None:
    form = OnboardingForm.model_validate(_load_json("haseeb_intake.json"))
    design = DesignPreferences.model_validate(_load_json("haseeb_design.json"))

    assert missing_required_fields(form) == ()
    assert design.model_dump(by_alias=True, mode="json")["imageSource"] == "placeholder"


def test_missing_required_fields_preserves_source_order_and_trims() -> None:
    form = OnboardingForm(
        company_name="  ",
        industry="Technology",
        business_activity="",
        target_audience="Teams",
        uvp="\t",
    )

    assert missing_required_fields(form) == (
        OnboardingField.COMPANY_NAME,
        OnboardingField.BUSINESS_ACTIVITY,
        OnboardingField.UVP,
    )
