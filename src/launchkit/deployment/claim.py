"""Application service coordinating claimable Vercel deployments."""

from urllib.parse import urlencode

from launchkit.deployment.archive import collect_deployment_files
from launchkit.deployment.contracts import V0ArchiveSource, VercelGateway
from launchkit.deployment.models import DeploymentResult, DeploymentStatus


class ClaimDeploymentService:
    """Deploy a completed v0 project and create its ownership-transfer URL."""

    def __init__(
        self,
        archive_source: V0ArchiveSource,
        vercel: VercelGateway,
        *,
        return_url: str = "http://localhost:8000/",
    ) -> None:
        self._archive_source = archive_source
        self._vercel = vercel
        self._return_url = return_url

    async def deploy(self, chat_id: str) -> DeploymentResult:
        archive = await self._archive_source.download_zip(chat_id)
        files = collect_deployment_files(archive.content)
        deployment = await self._vercel.create_deployment(chat_id, files)
        code = await self._vercel.create_transfer_code(deployment.project_id)
        claim_url = "https://vercel.com/claim-deployment?" + urlencode(
            {"code": code, "returnUrl": self._return_url}
        )
        return DeploymentResult(
            status=DeploymentStatus.READY_TO_CLAIM,
            chat_id=chat_id,
            project_id=deployment.project_id,
            deployment_id=deployment.deployment_id,
            live_url=f"https://{deployment.url}" if deployment.url else None,
            claim_url=claim_url,
            note=(
                "The site is building under the platform account. Share claimUrl with the "
                "business owner; accepting it transfers the project to their Vercel account."
            ),
        )
