"""
Media upload API schemas.

Place at: app/schemas/media_schema.py
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.media_model import MediaKind, MediaStatus


# ── Create upload (presign) ──────────────────────────────────────────────────

class CreateUploadRequest(BaseModel):
    filename: str
    content_type: str
    size: int = Field(..., gt=0, description="File size in bytes (client-declared)")

    # Cosmetic, for the instant placeholder. Computed client-side at capture so
    # the UI can show a blurred preview / reserve the box before the upload even
    # finishes. Re-confirmed server-side during processing.
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    blurhash: Optional[str] = None


class PresignedPart(BaseModel):
    part_number: int
    url: str


class CreateUploadResponse(BaseModel):
    asset_id: UUID
    object_key: str
    upload_strategy: str            # "single" | "multipart"
    expires_in: int

    # single
    upload_url: Optional[str] = None
    required_headers: dict = Field(default_factory=dict)

    # multipart
    multipart_upload_id: Optional[str] = None
    part_size: Optional[int] = None
    parts: Optional[list[PresignedPart]] = None


# ── Resume: re-presign multipart parts ───────────────────────────────────────

class PartUrlsResponse(BaseModel):
    asset_id: UUID
    part_size: int
    expires_in: int
    parts: list[PresignedPart]


# ── Finalize ──────────────────────────────────────────────────────────────────

class CompletedPart(BaseModel):
    part_number: int
    etag: str = Field(..., description="ETag header returned by R2 for this part")


class FinalizeUploadRequest(BaseModel):
    # Required for multipart uploads; ignored for single PUT.
    parts: Optional[list[CompletedPart]] = None


# ── Asset (returned by finalize + polled via GET /media/{id}) ────────────────

class MediaAssetResponse(BaseModel):
    asset_id: UUID
    kind: MediaKind
    status: MediaStatus
    content_type: str
    size: Optional[int] = None          # actual, verified size
    original_url: Optional[str] = None
    thumbnail_url: Optional[str] = None  # video poster (images: build transform URLs)
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    blurhash: Optional[str] = None
    created_at: datetime