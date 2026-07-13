"""Provider-neutral boundaries for claim deployment coordination."""

from collections.abc import Sequence
from typing import Protocol

from launchkit.deployment.models import DeploymentFile, VercelDeployment
from launchkit.generation.models import ArchiveDownload


class V0ArchiveSource(Protocol):
    async def download_zip(self, chat_id: str) -> ArchiveDownload:
        """Download a completed generated project archive."""


class VercelGateway(Protocol):
    async def create_deployment(
        self, chat_id: str, files: Sequence[DeploymentFile]
    ) -> VercelDeployment:
        """Create a production project deployment."""

    async def create_transfer_code(self, project_id_or_name: str) -> str:
        """Create a temporary project ownership-transfer code."""
