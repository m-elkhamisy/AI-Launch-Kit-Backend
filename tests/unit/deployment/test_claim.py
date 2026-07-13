"""Offline integration test for claim deployment coordination."""

import asyncio
import zipfile
from collections.abc import Sequence
from io import BytesIO

from launchkit.deployment import ClaimDeploymentService
from launchkit.deployment.models import DeploymentFile, VercelDeployment
from launchkit.generation.models import ArchiveDownload


class ArchiveSourceStub:
    async def download_zip(self, chat_id: str) -> ArchiveDownload:
        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("index.html", f"<h1>{chat_id}</h1>")
        return ArchiveDownload(content=output.getvalue(), filename="site.zip")


class VercelStub:
    def __init__(self) -> None:
        self.files: list[DeploymentFile] = []

    async def create_deployment(
        self, chat_id: str, files: Sequence[DeploymentFile]
    ) -> VercelDeployment:
        self.files = list(files)
        return VercelDeployment(
            project_id=f"project-{chat_id}", deployment_id="dep-1", url="site.vercel.app"
        )

    async def create_transfer_code(self, project_id_or_name: str) -> str:
        assert project_id_or_name == "project-chat-1"
        return "claim code"


def test_claim_deployment_coordinates_archive_deploy_and_transfer() -> None:
    vercel = VercelStub()
    service = ClaimDeploymentService(
        ArchiveSourceStub(), vercel, return_url="https://launchkit.example/complete"
    )

    result = asyncio.run(service.deploy("chat-1"))

    assert vercel.files[0].data == "<h1>chat-1</h1>"
    assert result.project_id == "project-chat-1"
    assert result.live_url == "https://site.vercel.app"
    assert "code=claim+code" in result.claim_url
    assert "returnUrl=https%3A%2F%2Flaunchkit.example%2Fcomplete" in result.claim_url
