"""Injected fake-client tests for S3 submission persistence."""

from collections.abc import Iterable, Mapping
from io import BytesIO
from typing import Any

import pytest
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from launchkit.core.exceptions import ApplicationError
from launchkit.storage import S3SubmissionStore, SubmissionNotFound, SubmissionStore


class FakePaginator:
    def __init__(self, pages: list[Mapping[str, Any]]) -> None:
        self.pages = pages
        self.kwargs: dict[str, Any] = {}

    def paginate(self, **kwargs: Any) -> Iterable[Mapping[str, Any]]:
        self.kwargs = kwargs
        return self.pages


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.paginator = FakePaginator([])

    def put_object(self, **kwargs: Any) -> object:
        self.objects[str(kwargs["Key"])] = bytes(kwargs["Body"])
        return {}

    def get_object(self, **kwargs: Any) -> Mapping[str, Any]:
        key = str(kwargs["Key"])
        if key not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": BytesIO(self.objects[key])}

    def get_paginator(self, operation_name: str) -> FakePaginator:
        assert operation_name == "list_objects_v2"
        return self.paginator


def test_s3_store_round_trip_and_prefix_contract() -> None:
    client = FakeS3Client()
    store: SubmissionStore = S3SubmissionStore(client, bucket="bucket", prefix="tenant/")

    saved = store.save_submission({"name": "Acme"}, "company-1")

    assert saved.normalized.name == "Acme"
    assert store.get_normalized_submission("company-1").name == "Acme"
    assert store.get_raw_submission("company-1").data == {"name": "Acme"}
    assert sorted(client.objects) == [
        "tenant/normalized/company-1.json",
        "tenant/raw/company-1.json",
    ]


def test_s3_store_lists_sorted_json_keys_and_ignores_invalid_pages() -> None:
    client = FakeS3Client()
    client.paginator.pages = [
        {"Contents": "invalid"},
        {
            "Contents": [
                {"Key": "normalized/b.json"},
                {"Key": "normalized/readme.txt"},
                {"Key": "normalized/a.json"},
                None,
            ]
        },
    ]
    store = S3SubmissionStore(client, bucket="bucket", prefix="")

    assert store.list_submissions() == ["a", "b"]
    assert client.paginator.kwargs == {"Bucket": "bucket", "Prefix": "normalized/"}


def test_s3_store_maps_missing_key_and_rejects_missing_bucket() -> None:
    client = FakeS3Client()
    with pytest.raises(ApplicationError):
        S3SubmissionStore(client, bucket="")
    store = S3SubmissionStore(client, bucket="bucket")
    with pytest.raises(SubmissionNotFound):
        store.get_raw_submission("missing")


def test_s3_store_rejects_non_object_payload() -> None:
    client = FakeS3Client()
    client.objects["submissions/raw/bad.json"] = b"[]"
    store = S3SubmissionStore(client, bucket="bucket")

    with pytest.raises(ApplicationError):
        store.get_raw_submission("bad")
