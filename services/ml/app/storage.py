"""MinIO object storage client (shared instance, bucket ml).

Reads source frames from the ``stream`` bucket (read-only scope) and writes
annotated + original images to the ``ml`` bucket, matching the
consolidated MinIO design in the architecture docs.
"""
from __future__ import annotations

import io
import logging
import os
import re
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: Optional[Minio] = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        _ensure_bucket(_client, settings.minio_ml_bucket)
    return _client


def _ensure_bucket(client: Minio, bucket: str) -> None:
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
    except S3Error as exc:  # pragma: no cover - depends on live minio
        logger.warning("MinIO bucket check failed for %s: %s", bucket, exc)


def _public_url(bucket: str, object_key: str) -> str:
    base = settings.minio_public_url.rstrip("/")
    return f"{base}/{bucket}/{object_key}"


def upload_image(bucket: str, object_key: str, data: bytes, content_type: str = "image/jpeg") -> str:
    client = get_client()
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return _public_url(bucket, object_key)


def upload_image_with_metadata(
    bucket: str,
    object_key: str,
    data: bytes,
    metadata: dict[str, str],
    content_type: str = "image/jpeg",
) -> str:
    client = get_client()
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
        metadata=metadata,
    )
    return _public_url(bucket, object_key)


def download_object(bucket: str, object_key: str) -> bytes:
    """Read an object (e.g. a frame from the stream bucket) as bytes."""
    client = get_client()
    resp = client.get_object(bucket, object_key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def object_exists(bucket: str, object_key: str) -> bool:
    client = get_client()
    try:
        client.stat_object(bucket, object_key)
        return True
    except S3Error:
        return False


def safe_object_key(prefix: str, name: str) -> str:
    """Build a timestamped, collision-free object key."""
    import datetime
    import random

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    salt = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    base = re.sub(r"[^a-zA-Z0-9._-]", "_", os.path.basename(name) or "image")
    return f"{prefix}/{now}_{salt}_{base}"


# Reject keys that could traverse out of their intended prefix/bucket. S3
# object keys legitimately use "/" as a path separator (e.g. "frames/foo.jpg"),
# so we allow slashes but block traversal (".."), a leading slash, backslashes
# or control characters, which could address unintended objects.
_KEY_UNSAFE = re.compile(r"(\.\.|\\|[\x00-\x1f\x7f])")


def is_safe_object_key(key: str) -> bool:
    """Return True only for a key that stays within its bucket (no traversal)."""
    if not key or not isinstance(key, str):
        return False
    if key.startswith("/") or _KEY_UNSAFE.search(key):
        return False
    return True

