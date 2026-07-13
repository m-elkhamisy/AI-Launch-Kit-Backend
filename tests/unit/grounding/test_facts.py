import json
from pathlib import Path

from launchkit.grounding import FACT_DISCIPLINE, render_fact_sheet
from launchkit.intake import OnboardingForm

FIXTURES = Path(__file__).parents[2] / "fixtures"


def test_fact_sheet_matches_haseeb_characterization_fixture() -> None:
    payload = json.loads((FIXTURES / "haseeb_intake.json").read_text(encoding="utf-8"))
    expected = (FIXTURES / "haseeb_fact_sheet.txt").read_text(encoding="utf-8").rstrip("\n")

    assert render_fact_sheet(OnboardingForm.model_validate(payload)) == expected


def test_fact_sheet_marks_every_empty_group_as_not_provided() -> None:
    fact_sheet = render_fact_sheet(OnboardingForm())

    assert fact_sheet.count("NOT PROVIDED") == 6
    assert "IDENTITY: NOT PROVIDED — do not invent" in fact_sheet
    assert "PROOF & STATS: NOT PROVIDED — do NOT invent stats" in fact_sheet


def test_fact_sheet_trims_values_and_omits_blank_fields() -> None:
    fact_sheet = render_fact_sheet(OnboardingForm(company_name="  Acme  ", industry="  "))

    assert "  - Company: Acme" in fact_sheet
    assert "Industry" not in fact_sheet.split("\n\n", maxsplit=1)[0]


def test_fact_discipline_keeps_source_safety_rules() -> None:
    assert FACT_DISCIPLINE.startswith("FACTUAL DISCIPLINE —")
    assert "Never fabricate a plausible-sounding number" in FACT_DISCIPLINE
    assert "never invent an address" in FACT_DISCIPLINE
