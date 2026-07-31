"""Replay persisted build status transitions as Server-Sent Events."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from launchkit.builds.service import event_view
from launchkit.builds.state import TERMINAL_BUILD_STATUSES
from launchkit.core.config import Settings
from launchkit.persistence import Database, PersistenceRepository


async def stream_build_events(
    database: Database,
    settings: Settings,
    *,
    build_id: str,
    owner_id: str,
    after_sequence: int,
) -> AsyncIterator[str]:
    last_sequence = max(0, after_sequence)
    last_heartbeat = datetime.now(UTC)
    while True:
        async with database.session() as session:
            repository = PersistenceRepository(session)
            build = await repository.get_build(build_id, owner_id)
            if build is None:
                return
            events = await repository.list_status_events(
                resource_type="build",
                resource_id=build_id,
                after_sequence=last_sequence,
            )
            for record in events:
                event = event_view(record)
                last_sequence = event.id
                yield (
                    f"id: {event.id}\n"
                    "event: status\n"
                    f"data: {event.model_dump_json(by_alias=True)}\n\n"
                )
            terminal = build.status in TERMINAL_BUILD_STATUSES
        if terminal:
            return
        now = datetime.now(UTC)
        if (now - last_heartbeat).total_seconds() >= settings.sse_heartbeat_seconds:
            yield ": heartbeat\n\n"
            last_heartbeat = now
        await asyncio.sleep(settings.sse_poll_seconds)
