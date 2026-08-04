"""Public representations of durable workflow resources."""

from datetime import datetime
from typing import Any

from launchkit.core.models import AliasedModel


class AssetView(AliasedModel):
    id: str
    kind: str
    filename: str
    label: str
    content_type: str
    size: int
    preview_url: str


class MockupView(AliasedModel):
    id: str
    generation: int
    ordinal: int
    label: str
    direction: str
    preview_url: str
    created_at: datetime


class MockupSelection(AliasedModel):
    mockup_id: str


class ProfileExtractionFromAsset(AliasedModel):
    asset_id: str


class OperationView(AliasedModel):
    id: str
    project_id: str | None
    kind: str
    status: str
    result: dict[str, Any]
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
