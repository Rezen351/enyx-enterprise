"""MinIO client for reading vision metadata."""

from __future__ import annotations

import json
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

        Prefers parsed JSON result files under ``results/`` because they carry
        the full detection payload (``root_length_cm``, ``tuber_size_cm``,
        ``condition``, ``confidence_avg``, ``num_detections``). Falls back to
        the ``detected/`` image prefix (custom ``x-amz-meta-*`` headers) when
        no JSON result is available yet.
        """
        json_meta = self._read_latest_json(module_id)
        if json_meta:
            return json_meta

        image_meta = self._read_latest_image_metadata(module_id)
        return image_meta

    def _read_latest_json(self, module_id: str) -> dict[str, Any]:
        candidates = [
            f"{self.prefix}/{module_id}/",
            f"{self.prefix}/",
        ]
        latest = None
        for prefix in candidates:
            try:
                objects = [
                    o
                    for o in self.client.list_objects(
                        self.bucket,
                        prefix=prefix,
                        recursive=True,
                    )
                    if o.object_name and o.object_name.endswith(".json")
                ]
                if objects:
                    candidate = max(objects, key=lambda o: o.last_modified)
                    if latest is None or candidate.last_modified > latest.last_modified:
                        latest = candidate
            except S3Error as exc:
                logger.error("MinIO list failed prefix=%s: %s", prefix, exc)

        if latest is None:
            return {}

        try:
            data = self.client.get_object(self.bucket, latest.object_name).read()
            payload = json.loads(data)
            detection = payload.get("detection", {})
            return {k: v for k, v in detection.items() if v is not None}
        except (S3Error, json.JSONDecodeError) as exc:
            logger.error("MinIO JSON read failed for %s: %s", latest.object_name, exc)
            return {}

    def _read_latest_image_metadata(self, module_id: str) -> dict[str, Any]:
        candidates = [
            f"{self.prefix}/{module_id}/",
            f"{self.prefix}/",
            "detected/",
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
            meta: dict[str, Any] = {}
            for k, v in obj.metadata.items():
                key = k.lower()
                if key.startswith("x-amz-meta-"):
                    key = key[len("x-amz-meta-") :]
                meta[key] = v[0] if isinstance(v, list) and v else v
            return meta
        except S3Error as exc:
            logger.error("MinIO stat failed: %s", exc)
            return {}
