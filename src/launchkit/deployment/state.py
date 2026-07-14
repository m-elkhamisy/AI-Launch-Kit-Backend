"""Persisted deployment transition rules."""

from launchkit.core.exceptions import DomainError
from launchkit.persistence.models import DeploymentRecord
from launchkit.persistence.repositories import PersistenceRepository

ACTIVE_DEPLOYMENT_STATUSES = frozenset({"queued", "creating", "building"})
TERMINAL_DEPLOYMENT_STATUSES = frozenset({"ready_to_claim", "completed", "failed", "cancelled"})
VALID_DEPLOYMENT_TRANSITIONS = {
    "queued": {"creating", "failed", "cancelled"},
    "creating": {"building", "ready_to_claim", "failed", "cancelled"},
    "building": {"ready_to_claim", "failed", "cancelled"},
    "ready_to_claim": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


async def transition_deployment(
    repository: PersistenceRepository,
    deployment: DeploymentRecord,
    status: str,
    *,
    message: str,
) -> None:
    previous = deployment.status
    if status == previous:
        if deployment.public_message == message:
            return
    elif status not in VALID_DEPLOYMENT_TRANSITIONS.get(previous, set()):
        raise DomainError(f"Invalid deployment transition from {previous} to {status}")
    deployment.status = status
    deployment.public_message = message
    await repository.add_status_event(
        resource_type="deployment",
        resource_id=deployment.id,
        from_status=previous,
        to_status=status,
        stage=status,
        message=message,
    )
