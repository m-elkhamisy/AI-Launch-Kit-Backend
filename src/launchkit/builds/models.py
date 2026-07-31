"""Public build contracts with private provider identifiers omitted."""

from datetime import datetime
from typing import Literal

from launchkit.core.models import AliasedModel

BuildStatus = Literal[
    "queued",
    "submitting",
    "running",
    "processing_result",
    "completed",
    "failed",
    "cancelled",
    "timed_out",
]


class BuildCreate(AliasedModel):
    provider: Literal["v0"] = "v0"


class BuildView(AliasedModel):
    id: str
    project_id: str
    provider: str
    status: BuildStatus
    stage: str
    message: str
    warnings: list[str]
    preview_url: str | None
    web_url: str | None
    download_url: str | None
    retry_after_seconds: int | None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None
    completed_at: datetime | None


class BuildEventView(AliasedModel):
    id: int
    status: str
    stage: str
    message: str
    created_at: datetime
