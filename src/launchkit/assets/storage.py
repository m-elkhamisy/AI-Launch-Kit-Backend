"""Local and S3 implementations for project-owned binary artifacts."""

from __future__ import annotations

import asyncio
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

from launchkit.core.config import Settings
from launchkit.core.exceptions import ConfigurationError

_OWNER_SEGMENT = re.compile(r"[^A-Za-z0-9._-]+")


class AssetBlobStore(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None:
        """Persist bytes under an internal storage key."""

    async def get(self, key: str) -> bytes:
        """Read bytes for an internal storage key."""


class ReadableBody(Protocol):
    def read(self) -> bytes:
        """Read bytes from an SDK response body."""


def project_asset_key(owner_id: str, project_id: str, *parts: str) -> str:
    """Build a tenant-scoped asset key: ``{owner}/projects/{project_id}/...``.

    Full S3 object key is ``{LAUNCHKIT_S3_ASSET_PREFIX}/{owner}/projects/...``.
    ``owner_id`` is the IC user subject (stable tenant partition). Put a shared
    org/licence segment in ``LAUNCHKIT_S3_ASSET_PREFIX`` when needed, e.g.
    ``uat/LIC-12345/assets/``.
    """

    owner = _OWNER_SEGMENT.sub("-", (owner_id or "").strip()).strip("-._")[:128] or "owner"
    return "/".join((owner, "projects", project_id, *parts))


def load_dotenv_file(path: Path | None = None) -> None:
    """Load ``.env`` into ``os.environ`` for keys boto3 expects (AWS_*), without overriding."""

    env_path = path or Path(".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


class LocalAssetBlobStore:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir.resolve()

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(content)
            temporary.replace(path)

        await asyncio.to_thread(write)

    async def get(self, key: str) -> bytes:
        path = self._path(key)

        def read() -> bytes:
            try:
                return path.read_bytes()
            except FileNotFoundError as exc:
                raise FileNotFoundError(
                    f"Uploaded asset is missing from worker storage ({key}). "
                    "API and worker must share local_data (or use S3)."
                ) from exc

        return await asyncio.to_thread(read)

    def _path(self, key: str) -> Path:
        path = (self._base_dir / key).resolve()
        if self._base_dir not in path.parents:
            raise ValueError("Asset storage key escapes the configured root")
        return path


class S3AssetBlobStore:
    def __init__(self, client: Any, *, bucket: str, prefix: str) -> None:
        self._client = client
        self._bucket = bucket
        self._prefix = prefix.strip("/")

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=self._key(key),
            Body=content,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object, Bucket=self._bucket, Key=self._key(key)
        )
        body = cast(Mapping[str, Any], response).get("Body")
        return await asyncio.to_thread(cast(ReadableBody, body).read)

    def _key(self, key: str) -> str:
        return f"{self._prefix}/{key}" if self._prefix else key


def _s3_client(region: str) -> Any:
    """Build an S3 client without triggering truststore/botocore SSL recursion.

    Prefer static keys via ``boto3.Session(...)`` so botocore never constructs the
    container-metadata credential provider (that path creates URLLib3Session and
    blows up after ``truststore.inject_into_ssl()``).
    """

    # Imported lazily so callers can skip truststore before this runs.
    import boto3  # noqa: PLC0415

    load_dotenv_file()
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")
    if access_key and secret_key:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
            region_name=region,
        )
        return session.client("s3")
    # IAM instance role / default chain — only safe when truststore was not injected.
    return boto3.Session(region_name=region).client("s3")


def create_asset_store(settings: Settings) -> AssetBlobStore:
    """Create local or S3 storage.

    Callers must skip ``use_system_certificates()`` when ``settings.s3_bucket`` is set,
    or pass static ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY``.
    """

    if not settings.s3_bucket:
        return LocalAssetBlobStore(settings.local_data_dir / "assets")
    if not settings.aws_region:
        raise ConfigurationError("LAUNCHKIT_AWS_REGION is required when S3 is enabled")
    client = _s3_client(settings.aws_region)
    return S3AssetBlobStore(
        client, bucket=settings.s3_bucket, prefix=settings.s3_asset_prefix
    )
