"""
Media asset system-of-record.

Every uploaded file (post image, video, chat attachment, ...) is tracked here
through its full lifecycle. The bytes live in Cloudflare R2; this table is the
authoritative record of *what* exists, *who* owns it, and *whether it's ready*.

Delivery model:
    IMAGE -> original stored in R2; size variants are produced on demand by
             Cloudflare edge transforms (/cdn-cgi/image/...). We do NOT store
             pre-resized files. The client requests the width it needs.
    VIDEO -> original stored in R2 (multipart upload); a poster frame is
             generated async (ffmpeg) and stored as the thumbnail.

Lifecycle (status):
    PENDING    -> presigned, awaiting the client's direct upload to R2
    UPLOADED   -> client called finalize; object verified present in R2
    PROCESSING -> metadata/poster being generated
    READY      -> safe to serve
    FAILED     -> processing failed (see failure_reason)
    EXPIRED    -> never uploaded within the presign window; reaped

The backend NEVER trusts the client for security-relevant facts: content_type
and size are declared at presign, then re-verified by a HEAD at finalize.
(width/height/blurhash are cosmetic, so a client-supplied value is fine for the
instant placeholder and is re-confirmed during processing.)
"""
from app.config.db.postgresql import Base
import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, UUID, ForeignKey, BigInteger, Integer, Enum, Index, JSON
from sqlalchemy.orm import relationship

class MediaKind(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"

class MediaStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # -- Object location in R2 (the ORIGINAL) -------------------------------
    # Namespaced per-owner so it's neither enumerable nor overwritable:
    #   media/{owner_id}/{asset_id}.{ext}
    bucket = Column(String, nullable=False)
    object_key = Column(String, nullable=False, unique=True)

    kind = Column(Enum(MediaKind), nullable=False)

    # -- Declared at presign, RE-VERIFIED at finalize via HEAD --------------
    content_type = Column(String, nullable=False)
    declared_size = Column(BigInteger, nullable=False)
    actual_size = Column(BigInteger)

    status = Column(Enum(MediaStatus), nullable=False, default=MediaStatus.PENDING)

    # -- Multipart session (large/video uploads). Set while a multipart upload
    #    is in flight so a dropped client can resume; cleared on completion. -
    multipart_upload_id = Column(String)

    # -- Public delivery (served via media.patterns.group, never the raw R2
    #    endpoint). For images, clients build /cdn-cgi/image/ transform URLs
    #    against original_url; derivatives holds only the video poster. ------
    original_url = Column(String)
    derivatives = Column(JSON, nullable=False, default=dict)  # video: {"thumbnail": url}

    # -- Render-without-jank metadata: the difference between "finished" and
    #    "work in progress". Sent by the client for an instant placeholder,
    #    re-confirmed during processing. --------------------------------------
    width = Column(Integer)          # px - lets the UI reserve the exact box
    height = Column(Integer)         # px
    duration_ms = Column(Integer)    # video only
    blurhash = Column(String)        # ~25-char blurred preview, shown before load

    failure_reason = Column(String)

    # -- Timestamps ---------------------------------------------------------
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    uploaded_at = Column(DateTime)
    ready_at = Column(DateTime)

    owner = relationship("User")

    __table_args__ = (
        Index("idx_media_owner", "owner_id"),
        Index("idx_media_status", "status"),
        # Orphan reaper scans PENDING assets older than the presign window.
        Index("idx_media_status_created", "status", "created_at"),
    )