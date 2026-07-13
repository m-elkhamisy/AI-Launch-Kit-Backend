"""Convert a project ZIP into Vercel's inline-file representation."""

import base64
import zipfile
from io import BytesIO

from launchkit.core.exceptions import DomainError
from launchkit.deployment.models import DeploymentFile

SKIP_NAMES = frozenset({".DS_Store"})
SKIP_PREFIXES = ("__MACOSX/",)


def collect_deployment_files(content: bytes) -> list[DeploymentFile]:
    files: list[DeploymentFile] = []
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if name in SKIP_NAMES or name.startswith(SKIP_PREFIXES):
                    continue
                raw = archive.read(info)
                try:
                    files.append(DeploymentFile(file=name, data=raw.decode("utf-8")))
                except UnicodeDecodeError:
                    files.append(
                        DeploymentFile(
                            file=name,
                            data=base64.b64encode(raw).decode("ascii"),
                            encoding="base64",
                        )
                    )
    except zipfile.BadZipFile as exc:
        raise DomainError("The generated project archive is not a valid ZIP file") from exc
    if not files:
        raise DomainError("The generated project archive contained no deployable files")
    return files
