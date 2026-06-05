from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional

from app.models.media_model import MediaKind, MediaStatus
from app.models.payment_model import Currency


# ── Write ─────────────────────────────────────────────────────────────────────

class ServiceUpdate(BaseModel):
    price: Optional[float] = Field(None, title="Price")
    price_history: Optional[UUID] = Field(None, title="Price History ID")
    vendor_id: Optional[str] = Field(None, title="Vendor ID")
    add_service_id: Optional[str] = Field(None, title="Service ID")
    description: Optional[str] = Field(None, title="Description")
    asset_ids: Optional[list[UUID]] = Field(None, title="Media asset IDs (ordered)")


# ── Media (resolved from media_assets at read time) ──────────────────────────
# One per asset referenced by a service. Resolved live so dimensions/blurhash/
# poster reflect current asset state — video posters arrive asynchronously after
# the worker runs, so a freshly-posted video starts UPLOADED and becomes READY.

class MediaItem(BaseModel):
    asset_id: UUID
    kind: MediaKind
    status: MediaStatus
    original_url: Optional[str] = None
    thumbnail_url: Optional[str] = None   # video poster; null for images
    width: Optional[int] = None
    height: Optional[int] = None
    duration_ms: Optional[int] = None
    blurhash: Optional[str] = None


# ── Read responses ────────────────────────────────────────────────────────────

class ServiceInfo(BaseModel):
    id: UUID
    price: Optional[float] = None
    description: Optional[str] = None
    add_vendor_id: UUID
    add_service_id: str


class VendorInfo(BaseModel):
    vendor_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    business_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None


class AddServiceInfo(BaseModel):
    id: str
    service_name: Optional[str] = None
    interval_minutes: Optional[int] = None


class PriceHistoryInfo(BaseModel):
    id: UUID
    price: Optional[float] = None
    price_minor: int
    currency: Currency


class FullServiceResponse(BaseModel):
    service: ServiceInfo
    vendor: VendorInfo
    add_service: AddServiceInfo
    price_history: PriceHistoryInfo
    media: list[MediaItem] = Field(default_factory=list)