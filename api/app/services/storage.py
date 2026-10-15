"""Product images in Cloud Storage (private bucket, no public URLs).

Uploaded images are validated, stored once per test, and passed to Gemini by
gs:// URI, so the 30 parallel Prompt 4 calls don't each carry the image bytes.
The web app shows the image through GET /tests/{test_id}/image.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
from functools import lru_cache

from google.cloud import storage

from app.config import get_settings

MAX_IMAGE_BYTES = 3 * 1024 * 1024
_EXT = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


class ImageError(ValueError):
    """Shown to the user as-is, so keep messages friendly."""


@lru_cache
def _client() -> storage.Client:
    return storage.Client(project=get_settings().gcp_project or None)


def sniff_mime(data: bytes) -> str | None:
    """Trust the file's bytes, not the browser's claimed type."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def decode_image(image_base64: str) -> tuple[bytes, str]:
    """Validate an uploaded base64 image. Returns (bytes, mime) or raises ImageError."""
    if len(image_base64) > MAX_IMAGE_BYTES * 4 // 3 + 4:
        raise ImageError("Image is too large. Please use one under 3 MB.")
    try:
        data = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError):
        raise ImageError("That image couldn't be read. Please try a different file.") from None
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageError("Image is too large. Please use one under 3 MB.")
    mime = sniff_mime(data)
    if mime is None:
        raise ImageError("Please upload a JPG, PNG or WebP image.")
    return data, mime


def _object_name(test_id: str, variant: str, mime: str) -> str:
    return f"tests/{test_id}/{variant}.{_EXT[mime]}"


def _upload(name: str, data: bytes, mime: str) -> str:
    bucket = get_settings().gcs_bucket
    blob = _client().bucket(bucket).blob(name)
    blob.upload_from_string(data, content_type=mime, timeout=30)
    return f"gs://{bucket}/{name}"


async def save_image(test_id: str, variant: str, data: bytes, mime: str) -> str | None:
    """Store an image; returns its gs:// URI, or None if storage isn't configured or fails.

    A failed upload never fails the test: the simulation just runs without the image.
    """
    if not get_settings().gcs_bucket:
        return None
    try:
        return await asyncio.to_thread(_upload, _object_name(test_id, variant, mime), data, mime)
    except Exception:  # noqa: BLE001 - storage outage must not break a live test
        import logging

        logging.getLogger("personapulse.storage").exception("Image upload failed for %s", test_id)
        return None


def _download(gcs_uri: str) -> tuple[bytes, str]:
    bucket, _, name = gcs_uri.removeprefix("gs://").partition("/")
    blob = _client().bucket(bucket).blob(name)
    data = blob.download_as_bytes(timeout=30)
    return data, blob.content_type or sniff_mime(data) or "application/octet-stream"


async def load_image(gcs_uri: str) -> tuple[bytes, str]:
    return await asyncio.to_thread(_download, gcs_uri)
