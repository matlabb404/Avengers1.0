"""
Media upload business logic: presign -> (client uploads to R2) -> finalize.

Security posture: the backend never trusts the client for security facts.
content_type and size are declared at presign, then RE-VERIFIED by a HEAD on
the object at finalize, and the object is deleted if it doesn't fit. Small files
get a single presigned PUT; large files (video) get a multipart session.

Place at: app/modules/media_module.py
"""
import logging
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from app.services.queue import enqueue_media_processing
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.account_model import User
from app.models.media_model import MediaAsset, MediaKind, MediaStatus
from app.schemas.media_schema import (
    CreateUploadRequest,
    CreateUploadResponse,
    FinalizeUploadRequest,
    MediaAssetResponse,
    PartUrlsResponse,
    PresignedPart,
)
from app.services.media import r2

logger = logging.getLogger(__name__)
settings = get_settings()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif",
}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES

_EXT = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
    "image/gif": ".gif", "image/heic": ".heic", "image/heif": ".heif",
    "video/mp4": ".mp4", "video/quicktime": ".mov", "video/webm": ".webm",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _kind_for(content_type: str) -> MediaKind:
    if content_type in ALLOWED_IMAGE_TYPES:
        return MediaKind.IMAGE
    if content_type in ALLOWED_VIDEO_TYPES:
        return MediaKind.VIDEO
    return MediaKind.FILE


def _ext_for(filename: str, content_type: str) -> str:
    return os.path.splitext(filename)[1].lower() or _EXT.get(content_type, "")


def _owned(db: Session, user: User, asset_id: UUID) -> MediaAsset:
    asset = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    # 404 (not 403) if it isn't theirs — don't leak that the id exists.
    if not asset or asset.owner_id != user.id:
        raise HTTPException(404, "Asset not found")
    return asset


def _presign_all_parts(key: str, upload_id: str, size: int, expires: int) -> list[PresignedPart]:
    part_size = settings.MEDIA_MULTIPART_PART_BYTES
    n = max(1, math.ceil(size / part_size))
    return [
        PresignedPart(part_number=i, url=r2.presign_part(key, upload_id, i, expires))
        for i in range(1, n + 1)
    ]


# ── Create upload (presign) ──────────────────────────────────────────────────

def create_upload(db: Session, user: User, req: CreateUploadRequest) -> CreateUploadResponse:
    if req.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported content type: {req.content_type}")
    if req.size <= 0 or req.size > settings.MEDIA_MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large. Max {settings.MEDIA_MAX_UPLOAD_BYTES} bytes.")

    kind = _kind_for(req.content_type)
    asset_id = uuid.uuid4()
    key = f"media/{user.id}/{asset_id}{_ext_for(req.filename, req.content_type)}"
    expires = settings.MEDIA_PRESIGN_EXPIRY_SECONDS

    asset = MediaAsset(
        id=asset_id,
        owner_id=user.id,
        bucket=settings.R2_BUCKET,
        object_key=key,
        kind=kind,
        content_type=req.content_type,
        declared_size=req.size,
        status=MediaStatus.PENDING,
        width=req.width,
        height=req.height,
        duration_ms=req.duration_ms,
        blurhash=req.blurhash,
        derivatives={},
    )

    # Small files: one PUT. Large files: multipart (resumable).
    if req.size <= settings.MEDIA_MULTIPART_THRESHOLD_BYTES:
        upload_url = r2.presign_put(key, req.content_type, expires)
        db.add(asset)
        db.commit()
        return CreateUploadResponse(
            asset_id=asset_id,
            object_key=key,
            upload_strategy="single",
            expires_in=expires,
            upload_url=upload_url,
            required_headers={"Content-Type": req.content_type},
        )

    upload_id = r2.create_multipart(key, req.content_type)
    asset.multipart_upload_id = upload_id
    db.add(asset)
    db.commit()

    return CreateUploadResponse(
        asset_id=asset_id,
        object_key=key,
        upload_strategy="multipart",
        expires_in=expires,
        multipart_upload_id=upload_id,
        part_size=settings.MEDIA_MULTIPART_PART_BYTES,
        parts=_presign_all_parts(key, upload_id, req.size, expires),
    )


# ── Resume: hand the client fresh part URLs for an in-flight multipart ────────

def get_upload_parts(db: Session, user: User, asset_id: UUID) -> PartUrlsResponse:
    asset = _owned(db, user, asset_id)
    if asset.status != MediaStatus.PENDING or not asset.multipart_upload_id:
        raise HTTPException(409, "No resumable multipart upload for this asset")

    expires = settings.MEDIA_PRESIGN_EXPIRY_SECONDS
    return PartUrlsResponse(
        asset_id=asset.id,
        part_size=settings.MEDIA_MULTIPART_PART_BYTES,
        expires_in=expires,
        parts=_presign_all_parts(
            asset.object_key, asset.multipart_upload_id, asset.declared_size, expires
        ),
    )


# ── Finalize ──────────────────────────────────────────────────────────────────

async def finalize_upload(
    db: Session, user: User, asset_id: UUID, req: FinalizeUploadRequest
) -> MediaAsset:
    asset = _owned(db, user, asset_id)

    # Idempotent: a retried finalize on an already-finalized asset just returns it.
    if asset.status in (MediaStatus.UPLOADED, MediaStatus.PROCESSING, MediaStatus.READY):
        return asset
    if asset.status != MediaStatus.PENDING:
        raise HTTPException(409, f"Cannot finalize (status={asset.status.value})")

    # Stitch the multipart upload together.
    if asset.multipart_upload_id:
        if not req.parts:
            raise HTTPException(400, "Multipart finalize requires the list of parts")
        parts = sorted(
            ({"ETag": p.etag, "PartNumber": p.part_number} for p in req.parts),
            key=lambda p: p["PartNumber"],
        )
        try:
            r2.complete_multipart(asset.object_key, asset.multipart_upload_id, parts)
        except Exception as e:
            raise HTTPException(400, f"Failed to complete multipart upload: {e}")

    # Never trust the client — confirm the object truly landed and re-check size.
    meta = r2.head(asset.object_key)
    if meta is None:
        raise HTTPException(400, "Object not found in storage — upload incomplete")

    if meta["size"] > settings.MEDIA_MAX_UPLOAD_BYTES:
        r2.delete(asset.object_key)
        asset.status = MediaStatus.FAILED
        asset.failure_reason = "Uploaded object exceeds max size"
        db.commit()
        raise HTTPException(413, "Uploaded object exceeds max size")

    asset.actual_size = meta["size"]
    asset.multipart_upload_id = None
    asset.uploaded_at = datetime.now(timezone.utc)
    asset.original_url = r2.public_url(asset.object_key)

    if asset.kind == MediaKind.IMAGE:
        # Variants come from Cloudflare edge transforms and the client already
        # supplied blurhash + dimensions, so an image is servable the instant
        # it's uploaded — no worker needed.
        asset.status = MediaStatus.READY
        asset.ready_at = datetime.now(timezone.utc)
    else:
            # Video (and other) need a poster frame + metadata: the async worker
            # claims UPLOADED assets and moves them to READY.
            asset.status = MediaStatus.UPLOADED

    db.commit()
    db.refresh(asset)
    # Enqueue AFTER commit so the worker can't race to read the row before it's
    # visible. Only videos/files need processing; images are already READY.
    if asset.status == MediaStatus.UPLOADED:
        await enqueue_media_processing(asset.id)
    return asset


# ── Read / cancel ──────────────────────────────────────────────────────────────

def get_asset(db: Session, user: User, asset_id: UUID) -> MediaAsset:
    return _owned(db, user, asset_id)


def abort_upload(db: Session, user: User, asset_id: UUID) -> dict:
    asset = _owned(db, user, asset_id)
    if asset.multipart_upload_id:
        r2.abort_multipart(asset.object_key, asset.multipart_upload_id)
    if asset.status == MediaStatus.PENDING:
        db.delete(asset)
        db.commit()
    return {"status": "aborted"}


# ── Maintenance: reap presigned-but-never-uploaded assets ─────────────────────

def reap_orphans(db: Session) -> dict:
    """
    Delete PENDING assets that were presigned but never uploaded within the TTL,
    abort any dangling multipart session, and remove partial bytes. Wire to cron
    or the arq scheduler.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.MEDIA_PENDING_TTL_SECONDS)
    stale = db.query(MediaAsset).filter(
        MediaAsset.status == MediaStatus.PENDING,
        MediaAsset.created_at <= cutoff,
    ).all()

    reaped = 0
    for asset in stale:
        if asset.multipart_upload_id:
            r2.abort_multipart(asset.object_key, asset.multipart_upload_id)
        r2.delete(asset.object_key)  # clear any partial single-PUT bytes
        asset.status = MediaStatus.EXPIRED
        reaped += 1

    if reaped:
        db.commit()
        logger.info("Reaped %d orphaned media uploads", reaped)
    return {"reaped": reaped}

# ── DB model -> response DTO ─────────────────────────────────────────────────

def _to_response(asset: MediaAsset) -> MediaAssetResponse:
    derivatives = asset.derivatives or {}
    return MediaAssetResponse(
        asset_id=asset.id,
        kind=asset.kind,
        status=asset.status,
        content_type=asset.content_type,
        size=asset.actual_size,
        original_url=asset.original_url,
        thumbnail_url=derivatives.get("thumbnail"),
        width=asset.width,
        height=asset.height,
        duration_ms=asset.duration_ms,
        blurhash=asset.blurhash,
        created_at=asset.created_at,
    )