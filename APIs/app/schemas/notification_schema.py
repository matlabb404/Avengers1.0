from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID
from pydantic import BaseModel, Field


# ── Per-notification output ───────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: UUID
    type: str                          # NotificationType.*
    actor_user_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    target_type: Optional[str] = None  # NotificationTarget.*
    target_id: Optional[str] = None
    preview: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationPage(BaseModel):
    items: List[NotificationOut]
    next_cursor: Optional[str] = None   # keyset cursor (created_at ISO of last item)
    unread_count: int = 0               # convenience: current unread total


class UnreadCountOut(BaseModel):
    unread_count: int


class MarkReadOut(BaseModel):
    ok: bool
    unread_count: int


# ── Preferences ───────────────────────────────────────────────────────────────

class TypePref(BaseModel):
    push: bool = True
    show: bool = True


class PreferencesOut(BaseModel):
    """The full effective preference map: every known type present, with defaults
       filled in for any the user hasn't explicitly set."""
    prefs: Dict[str, TypePref]


class PreferencesUpdate(BaseModel):
    """Partial update: only the types included are changed; others are untouched.
       e.g. {"prefs": {"FOLLOW": {"push": false, "show": true}}}"""
    prefs: Dict[str, TypePref] = Field(default_factory=dict)


# ── Internal create payload (used by other modules via create_notification) ───
# Not an HTTP body — features build this when emitting an event.

class NotificationCreate(BaseModel):
    recipient_user_id: UUID
    type: str
    actor_user_id: Optional[UUID] = None
    actor_name: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    preview: Optional[str] = None


# ── Per-vendor mute ───────────────────────────────────────────────────────────

class VendorMuteOut(BaseModel):
    """The types this user has muted for a given vendor."""
    vendor_id: UUID
    muted_types: List[str]


class VendorMuteUpdate(BaseModel):
    """Set the mute state for one type on one vendor.
       e.g. {"type": "BIG_SERVICE", "muted": true}"""
    type: str
    muted: bool