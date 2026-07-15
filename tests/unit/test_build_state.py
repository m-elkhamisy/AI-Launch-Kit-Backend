"""Build transition invariants."""

import asyncio
from typing import Any, cast

import pytest

from launchkit.builds.state import transition_build
from launchkit.core.exceptions import DomainError
from launchkit.persistence.models import BuildRecord
from launchkit.persistence.repositories import PersistenceRepository


class EventRepository:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def add_status_event(self, **event: Any) -> None:
        self.events.append(event)


def record() -> BuildRecord:
    return BuildRecord(
        id="build-1",
        project_id="project-1",
        provider="v0",
        status="running",
        stage="generating",
        message="Generating website",
    )


def test_transition_build_skips_an_identical_event() -> None:
    repository = EventRepository()
    build = record()

    asyncio.run(
        transition_build(
            cast(PersistenceRepository, repository),
            build,
            "running",
            stage="generating",
            message="Generating website",
        )
    )

    assert repository.events == []


def test_transition_build_records_same_status_progress_and_rejects_invalid_change() -> None:
    repository = EventRepository()
    build = record()
    asyncio.run(
        transition_build(
            cast(PersistenceRepository, repository),
            build,
            "running",
            stage="finalizing",
            message="Finalizing archive",
        )
    )

    with pytest.raises(DomainError, match="running to queued"):
        asyncio.run(
            transition_build(
                cast(PersistenceRepository, repository),
                build,
                "queued",
                stage="queued",
                message="Queued again",
            )
        )

    assert build.stage == "finalizing"
    assert repository.events[0]["from_status"] == "running"
    assert repository.events[0]["to_status"] == "running"
