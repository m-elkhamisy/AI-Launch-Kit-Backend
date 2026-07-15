"""Durable Vercel claim-deployment worker handler."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from launchkit.adapters.vercel import VercelAdapter
from launchkit.assets import AssetBlobStore
from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError
from launchkit.deployment.claim import ClaimDeploymentService
from launchkit.deployment.contracts import VercelGateway
from launchkit.deployment.models import DeploymentResult
from launchkit.deployment.state import TERMINAL_DEPLOYMENT_STATUSES, transition_deployment
from launchkit.generation.models import ArchiveDownload
from launchkit.persistence.models import BuildRecord, DeploymentRecord, JobRecord, ProjectRecord
from launchkit.persistence.repositories import PersistenceRepository


class StoredArchiveSource:
    def __init__(self, content: bytes, filename: str) -> None:
        self._archive = ArchiveDownload(content=content, filename=filename)

    async def download_zip(self, chat_id: str) -> ArchiveDownload:
        del chat_id
        return self._archive


class DeploymentJobHandlers:
    def __init__(
        self,
        settings: Settings,
        asset_store: AssetBlobStore,
        *,
        vercel: VercelGateway | None,
    ) -> None:
        self._settings = settings
        self._asset_store = asset_store
        self._vercel = vercel

    @property
    def handlers(self) -> dict[str, Callable[[JobRecord, AsyncSession], Awaitable[None]]]:
        return {"deployment.create": self.create}

    async def create(self, job: JobRecord, session: AsyncSession) -> None:
        deployment = await session.get(DeploymentRecord, str(job.payload.get("deploymentId", "")))
        if deployment is None:
            raise RuntimeError("Deployment job has no deployment")
        if deployment.status != "queued" or deployment.status in TERMINAL_DEPLOYMENT_STATUSES:
            return
        repository = PersistenceRepository(session)
        try:
            if self._vercel is None:
                raise ConfigurationError("Vercel is not configured")
            build = await session.get(BuildRecord, deployment.build_id)
            if build is None or build.status != "completed" or build.archive_asset_id is None:
                raise RuntimeError("Completed build archive is missing")
            asset = await repository.get_asset_for_project(build.archive_asset_id, build.project_id)
            if asset is None:
                raise RuntimeError("Deployment archive asset is missing")
            content = await self._asset_store.get(asset.storage_key)
            await transition_deployment(
                repository,
                deployment,
                "creating",
                message="Creating the Vercel deployment",
            )
            await session.commit()

            coordinator = ClaimDeploymentService(
                StoredArchiveSource(content, asset.filename),
                self._vercel,
                return_url=self._settings.claim_return_url,
            )
            result = await coordinator.deploy(deployment.id)
            await self._persist_result(repository, deployment, result)
            project = await session.get(ProjectRecord, build.project_id)
            if project is not None:
                project.status = "deployment_ready"
        except Exception:
            if deployment.status not in TERMINAL_DEPLOYMENT_STATUSES:
                await transition_deployment(
                    repository,
                    deployment,
                    "failed",
                    message="The website could not be deployed to Vercel",
                )
                deployment.completed_at = datetime.now(UTC)
            raise

    async def _persist_result(
        self,
        repository: PersistenceRepository,
        deployment: DeploymentRecord,
        result: DeploymentResult,
    ) -> None:
        await transition_deployment(
            repository, deployment, "building", message="Vercel is building the website"
        )
        await repository.add_provider_reference(
            resource_type="deployment",
            resource_id=deployment.id,
            provider="vercel",
            reference_type="project_id",
            reference_value=result.project_id,
        )
        if result.deployment_id:
            await repository.add_provider_reference(
                resource_type="deployment",
                resource_id=deployment.id,
                provider="vercel",
                reference_type="deployment_id",
                reference_value=result.deployment_id,
            )
        deployment.live_url = result.live_url
        deployment.claim_url = result.claim_url
        deployment.claim_expires_at = datetime.now(UTC) + timedelta(hours=24)
        await transition_deployment(
            repository,
            deployment,
            "ready_to_claim",
            message="The website is ready to claim on Vercel",
        )


def create_deployment_job_handlers(
    settings: Settings, client: httpx.AsyncClient, asset_store: AssetBlobStore
) -> DeploymentJobHandlers:
    token = settings.vercel_token.get_secret_value() if settings.vercel_token else ""
    vercel = (
        VercelAdapter(
            client,
            token=token,
            team_id=settings.vercel_team_id,
            base_url=settings.vercel_base_url,
        )
        if token
        else None
    )
    return DeploymentJobHandlers(settings, asset_store, vercel=vercel)
