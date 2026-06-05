"""
Thin Cloudflare R2 (S3-compatible) client for the media pipeline.

Only the operations the upload flow needs: presigned single PUT, presigned
multipart, verification (HEAD), and cleanup. Kept separate from the legacy
app/services/storage.py so the media system carries no dependency on it.

Place at: app/services/media/r2.py
(add an empty app/services/media/__init__.py alongside it)
"""
import logging
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config.settings import get_settings
from app.services.media import r2_presign

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache forever: object keys carry a unique asset id, so the bytes never change.
IMMUTABLE_CACHE = "public, max-age=31536000, immutable"

_client = boto3.client(
    "s3",
    endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    region_name="auto",
)

_R2_HOST = f"{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

BUCKET = settings.R2_BUCKET


def public_url(key: str) -> str:
    """CDN URL for an object (served via the media.* custom domain)."""
    return f"{settings.R2_PUBLIC_BASE_URL}/{key}"


# ── Single PUT ────────────────────────────────────────────────────────────────

def presign_put(key: str, content_type: str, expires: int) -> str:
    """
    Presigned URL for a single-shot PUT. content_type is baked into the
    signature, so the client must send exactly that Content-Type header — it
    cannot upload a different type than it declared.
    """
    return r2_presign.presign_put(
        key=key, content_type=content_type, expires=expires,
        host=_R2_HOST, access_key=settings.R2_ACCESS_KEY_ID, secret_key=settings.R2_SECRET_ACCESS_KEY,
        bucket=BUCKET
    )

def download(key: str, dest: str) -> None:
    _client.download_file(BUCKET, key, dest)


def upload_file(local_path: str, key: str, content_type: str) -> None:
    _client.upload_file(
        local_path, BUCKET, key,
        ExtraArgs={"ContentType": content_type, "CacheControl": IMMUTABLE_CACHE},
    )

# ── Multipart ─────────────────────────────────────────────────────────────────

def create_multipart(key: str, content_type: str) -> str:
    resp = _client.create_multipart_upload(
        Bucket=BUCKET,
        Key=key,
        ContentType=content_type,
        CacheControl=IMMUTABLE_CACHE,
    )
    return resp["UploadId"]


def presign_part(key: str, upload_id: str, part_number: int, expires: int) -> str:
    """
    Presigned URL for a multipart upload part. The client must send a PUT to
    that URL with the exact Content-Type declared at multipart creation time.
    """
    return r2_presign.presign_part(
        key=key, upload_id=upload_id, part_number=part_number, expires=expires,
        host=_R2_HOST, access_key=settings.R2_ACCESS_KEY_ID, secret_key=settings.R2_SECRET_ACCESS_KEY,
        bucket=BUCKET
    )


def complete_multipart(key: str, upload_id: str, parts: list) -> None:
    """parts: [{"ETag": "...", "PartNumber": 1}, ...] in ascending order."""
    _client.complete_multipart_upload(
        Bucket=BUCKET,
        Key=key,
        UploadId=upload_id,
        MultipartUpload={"Parts": parts},
    )


def abort_multipart(key: str, upload_id: str) -> None:
    try:
        _client.abort_multipart_upload(Bucket=BUCKET, Key=key, UploadId=upload_id)
    except ClientError:
        logger.warning("Failed to abort multipart upload key=%s id=%s", key, upload_id)


# ── Verify / cleanup ────────────────────────────────────────────────────────────

def head(key: str) -> Optional[dict]:
    """Return {'size', 'content_type'} for an object, or None if it's missing."""
    try:
        resp = _client.head_object(Bucket=BUCKET, Key=key)
        return {"size": resp["ContentLength"], "content_type": resp.get("ContentType", "")}
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def delete(key: str) -> None:
    try:
        _client.delete_object(Bucket=BUCKET, Key=key)
    except ClientError:
        logger.warning("Failed to delete object key=%s", key)