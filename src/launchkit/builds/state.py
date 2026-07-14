"""Enforced internal build state transitions and persisted status history."""

from launchkit.core.exceptions import DomainError
from launchkit.persistence.models import BuildRecord
from launchkit.persistence.repositories import PersistenceRepository

TERMINAL_BUILD_STATUSES = frozenset({"completed", "failed", "cancelled", "timed_out"})
ACTIVE_BUILD_STATUSES = frozenset({"queued", "submitting", "running", "processing_result"})
VALID_TRANSITIONS = {
    "queued": {"submitting", "failed", "cancelled"},
    "submitting": {"running", "processing_result", "completed", "failed", "timed_out"},
    "running": {"processing_result", "completed", "failed", "timed_out"},
    "processing_result": {"completed", "failed", "timed_out"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
    "timed_out": set(),
}


async def transition_build(
    repository: PersistenceRepository,
    build: BuildRecord,
    status: str,
    *,
    stage: str,
    message: str,
) -> None:
    previous = build.status
    if status == previous:
        if build.stage == stage and build.message == message:
            return
    elif status not in VALID_TRANSITIONS.get(previous, set()):
        raise DomainError(f"Invalid build transition from {previous} to {status}")
    build.status = status
    build.stage = stage
    build.message = message
    await repository.add_status_event(
        resource_type="build",
        resource_id=build.id,
        from_status=previous,
        to_status=status,
        stage=stage,
        message=message,
    )
