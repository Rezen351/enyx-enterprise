"""MinIO client for reading vision metadata."""

from __future__ import annotations

import logging
from typing import Any

from minio import Minio
from minio.error import S3Error

from .config import settings

logger = logging.getLogger("ppo-control")


class MinIOClient:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self.bucket = settings.MINIO_BUCKET
        self.prefix = settings.MINIO_PREFIX

    def get_latest_metadata(self, module_id: str) -> dict[str, Any]:
        """Return the latest detection metadata for a module.

        Falls back to scanning all result prefixes if the module-prefixed path
        is empty, because the Stream Service stores results by stream name
        (results/<stream_name>/...) rather than by module id.
        """
        candidates = [
            f"{self.prefix}/{module_id}/",
            f"{self.prefix}/",
        ]
        latest = None
        for prefix in candidates:
            try:
                objects = list(
                    self.client.list_objects(
                        self.bucket,
                        prefix=prefix,
                        recursive=True,
                    )
                )
                if objects:
                    candidate = max(objects, key=lambda o: o.last_modified)
                    if latest is None or candidate.last_modified > latest.last_modified:
                        latest = candidate
            except S3Error as exc:
                logger.error("MinIO list failed prefix=%s: %s", prefix, exc)

        if latest is None:
            return {}

        try:
            obj = self.client.stat_object(self.bucket, latest.object_name)
            meta = {}
            for k, v in obj.metadata.items():
                key = k.lower()
                if key.startswith("x-amz-meta-"):
                    key = key[len("x-amz-meta-") :]
                meta[key] = v[0] if isinstance(v, list) and v else v
            return meta
        except S3Error as exc:
            logger.error("MinIO stat failed: %s", exc)
            return {}
