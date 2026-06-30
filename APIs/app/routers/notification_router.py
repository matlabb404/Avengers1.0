"""
Notification REST endpoints.

  GET    /notifications                 -> paginated feed (newest first) + unread
  GET    /notifications/unread_count    -> just the unread badge number
  POST   /notifications/{id}/read       -> mark one read
  POST   /notifications/read_all        -> mark all read
  GET    /notifications/preferences     -> full effective per-type prefs
  PUT    /notifications/preferences     -> partial update of per-type prefs

Auth: same as the rest of the app — get_current_user returns the User (with .id).
"""
from typing import Optional
from uuid import UUID
 
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
 
from app.config.db.postgresql import SessionLocal
from app.modules.account_module import get_current_user
from app.models.account_model import User
from app.modules import notification_module as nm
from app.modules import device_token_module as dt
from app.schemas.device_token_schema import (
    RegisterTokenRequest,
    RegisterTokenResponse,
    UnregisterTokenRequest,
)
from app.schemas.notification_schema import (
    NotificationPage,
    UnreadCountOut,
    MarkReadOut,
    PreferencesOut,
    PreferencesUpdate,
    VendorMuteOut,
    VendorMuteUpdate,
)
from uuid import UUID as _UUID

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=NotificationPage)
def list_notifications(
    limit: int = Query(30, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="created_at ISO of the last item from the previous page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return nm.list_notifications(db, current_user.id, limit=limit, cursor=cursor)


@router.get("/unread_count", response_model=UnreadCountOut)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UnreadCountOut(unread_count=nm.unread_count(db, current_user.id))


@router.post("/{notification_id}/read", response_model=MarkReadOut)
def mark_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_unread = nm.mark_read(db, current_user.id, notification_id)
    return MarkReadOut(ok=True, unread_count=new_unread)


@router.post("/read_all", response_model=MarkReadOut)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_unread = nm.mark_all_read(db, current_user.id)
    return MarkReadOut(ok=True, unread_count=new_unread)


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PreferencesOut(prefs=nm.get_preferences(db, current_user.id))


@router.put("/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = nm.update_preferences(db, current_user.id, body.prefs)
    return PreferencesOut(prefs=updated)

# ── Per-vendor mute (from the vendor profile options button) ──────────────────

@router.get("/vendor/{vendor_id}/mutes", response_model=VendorMuteOut)
def get_vendor_mutes(
    vendor_id: _UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Which notification types this user has muted for this vendor."""
    types = nm.list_vendor_mutes(db, current_user.id, vendor_id)
    return VendorMuteOut(vendor_id=vendor_id, muted_types=types)


@router.put("/vendor/{vendor_id}/mute", response_model=VendorMuteOut)
def set_vendor_mute(
    vendor_id: _UUID,
    body: VendorMuteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mute/unmute one notification type for this vendor (idempotent)."""
    nm.set_vendor_mute(db, current_user.id, vendor_id, body.type, body.muted)
    types = nm.list_vendor_mutes(db, current_user.id, vendor_id)
    return VendorMuteOut(vendor_id=vendor_id, muted_types=types)


# ── Push device tokens (register on login / token refresh) ────────────────────

@router.post("/devices/register", response_model=RegisterTokenResponse)
def register_device(
    body: RegisterTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register (or refresh) this device's push token. Idempotent."""
    try:
        dt.register_token(db, current_user.id, body.token, body.platform)
    except ValueError:
        return RegisterTokenResponse(ok=False)
    return RegisterTokenResponse(ok=True)


@router.post("/devices/unregister", response_model=RegisterTokenResponse)
def unregister_device(
    body: UnregisterTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove this device's push token (logout)."""
    dt.unregister_token(db, current_user.id, body.token)
    return RegisterTokenResponse(ok=True)