"""Local and S3 implementations for project-owned binary artifacts."""

import asyncio
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]

from launchkit.core.config import Settings


class AssetBlobStore(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None:
        """Persist bytes under an internal storage key."""

    async def get(self, key: str) -> bytes:
        """Read bytes for an internal storage key."""


class ReadableBody(Protocol):
    def read(self) -> bytes:
        """Read bytes from an SDK response body."""


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
        return await asyncio.to_thread(self._path(key).read_bytes)

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


def create_asset_store(settings: Settings) -> AssetBlobStore:
    if settings.s3_bucket:
        client = boto3.client("s3", region_name=settings.aws_region)
        return S3AssetBlobStore(client, bucket=settings.s3_bucket, prefix=settings.s3_asset_prefix)
    return LocalAssetBlobStore(settings.local_data_dir / "assets")
