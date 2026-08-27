from __future__ import annotations

import io
from typing import BinaryIO, Optional

from app.core.config import settings


class StorageService:
    """Abstract storage adapter for models, datasets, reports, and backups."""

    def __init__(self, backend: Optional[str] = None) -> None:
        self.backend = (backend or settings.STORAGE_BACKEND).lower()

    def upload(self, key: str, data: bytes | BinaryIO, content_type: str = "application/octet-stream") -> str:
        if self.backend == "s3":
            return f"s3://{settings.STORAGE_BUCKET}/{key}"
        if self.backend == "gcs":
            return f"gs://{settings.STORAGE_BUCKET}/{key}"
        if self.backend == "azure":
            return f"az://{settings.STORAGE_BUCKET}/{key}"
        if self.backend == "minio":
            return f"minio://{settings.STORAGE_BUCKET}/{key}"
        return f"local://{key}"

    def download(self, key: str) -> bytes:
        return b""

    def exists(self, key: str) -> bool:
        return False

    def delete(self, key: str) -> bool:
        return True


storage_service = StorageService()
