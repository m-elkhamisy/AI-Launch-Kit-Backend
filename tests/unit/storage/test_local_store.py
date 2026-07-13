"""Local submission-store contract tests."""

import json
from pathlib import Path

import pytest

from launchkit.core.exceptions import ApplicationError, DomainError
from launchkit.storage import LocalSubmissionStore, SubmissionNotFound, SubmissionStore


def test_local_store_round_trip_and_legacy_file_layout(tmp_path: Path) -> None:
    store: SubmissionStore = LocalSubmissionStore(tmp_path)

    saved = store.save_submission({"businessName": "Acme", "services": ["A", "B"]}, "id-2")
    store.save_submission({"name": "Beta"}, "id-1")

    assert saved.normalized.name == "Acme"
    assert store.get_normalized_submission("id-2").services == "A; B"
    assert store.get_raw_submission("id-2").data == {
        "businessName": "Acme",
        "services": ["A", "B"],
    }
    assert store.list_submissions() == ["id-1", "id-2"]
    raw_path = tmp_path / "submissions" / "raw" / "id-2.json"
    assert json.loads(raw_path.read_text(encoding="utf-8"))["id"] == "id-2"
    assert not raw_path.with_suffix(".tmp").exists()


def test_local_store_generates_id_and_maps_missing_or_invalid_ids(tmp_path: Path) -> None:
    store = LocalSubmissionStore(tmp_path)

    assert len(store.save_submission({}).id) == 32
    with pytest.raises(SubmissionNotFound):
        store.get_raw_submission("missing")
    with pytest.raises(DomainError):
        store.get_raw_submission("../escape")


def test_local_store_rejects_corrupt_non_object_json(tmp_path: Path) -> None:
    store = LocalSubmissionStore(tmp_path)
    path = tmp_path / "submissions" / "raw" / "bad.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ApplicationError):
        store.get_raw_submission("bad")
