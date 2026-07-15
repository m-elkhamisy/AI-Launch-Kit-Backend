"""Idempotent deployment creation and owned reads."""

import hashlib
import json

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError, DomainError
from launchkit.deployment.models import DeploymentCreate, DeploymentStatus, DeploymentView
from launchkit.deployment.state import ACTIVE_DEPLOYMENT_STATUSES
from launchkit.persistence.models import DeploymentRecord
from launchkit.persistence.repositories import PersistenceRepository


class DeploymentNotFoundError(DomainError):
    """Raised when a deployment or its build is not owned by the testing user."""


class DeploymentService:
    def __init__(
        self, repository: PersistenceRepository, owner_id: str, settings: Settings
    ) -> None:
        self._repository = repository
        self._owner_id = owner_id
        self._settings = settings

    async def start(
        self, build_id: str, request: DeploymentCreate, idempotency_key: str
    ) -> DeploymentView:
        build = await self._repository.get_build(build_id, self._owner_id)
        if build is None:
            raise DeploymentNotFoundError("Build not found")
        if self._settings.vercel_token is None:
            raise ConfigurationError("Vercel is required for deployment")
        if build.status != "completed" or build.archive_asset_id is None:
            raise DomainError("Complete the website build before deploying it.")
        if request.provider != "vercel":
            raise DomainError("Only Vercel deployments are supported.")
        normalized_key = idempotency_key.strip()
        if not normalized_key or len(normalized_key) > 200:
            raise DomainError("A valid Idempotency-Key header is required.")
        scope = f"builds:{build_id}:deployments"
        key_hash = hashlib.sha256(normalized_key.encode()).hexdigest()
        request_hash = hashlib.sha256(
            json.dumps(
                [request.model_dump(mode="json"), build.archive_asset_id],
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        existing = await self._repository.get_idempotency(
            owner_id=self._owner_id, scope=scope, key_hash=key_hash
        )
        if existing is not None:
            if existing.request_hash != request_hash:
                raise DomainError(
                    "This idempotency key was already used for a different deployment."
                )
            deployment = await self._repository.get_deployment(existing.resource_id, self._owner_id)
            if deployment is None:
                raise DeploymentNotFoundError("Deployment not found")
            return deployment_view(deployment)
        active = await self._repository.find_active_deployment(build_id)
        if active is not None:
            return deployment_view(active)
        deployment = await self._repository.add_deployment(build_id=build.id)
        await self._repository.add_status_event(
            resource_type="deployment",
            resource_id=deployment.id,
            from_status=None,
            to_status="queued",
            stage="queued",
            message="Deployment queued",
        )
        await self._repository.enqueue_job("deployment.create", {"deploymentId": deployment.id})
        await self._repository.add_idempotency(
            owner_id=self._owner_id,
            scope=scope,
            key_hash=key_hash,
            request_hash=request_hash,
            resource_type="deployment",
            resource_id=deployment.id,
        )
        project = await self._repository.get_project_for_build(build.id)
        if project is not None:
            project.latest_deployment_id = deployment.id
            project.status = "deployment_queued"
        await self._repository.commit()
        return deployment_view(deployment)

    async def get(self, deployment_id: str) -> DeploymentView:
        deployment = await self._repository.get_deployment(deployment_id, self._owner_id)
        if deployment is None:
            raise DeploymentNotFoundError("Deployment not found")
        return deployment_view(deployment)


def deployment_view(record: DeploymentRecord) -> DeploymentView:
    return DeploymentView(
        id=record.id,
        build_id=record.build_id,
        status=DeploymentStatus(record.status),
        live_url=record.live_url,
        claim_url=record.claim_url,
        claim_expires_at=record.claim_expires_at,
        message=record.public_message,
        retry_after_seconds=5 if record.status in ACTIVE_DEPLOYMENT_STATUSES else None,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
