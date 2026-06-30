"""
Notifications: the single module every feature calls to emit an event, plus the
read/list/preferences operations the router exposes.

Design:
  * Rows are ALWAYS created (the in-app feed is complete). The user's per-type
    preference only decides whether a row is shown in the feed (`show`) and/or
    pushed via FCM later (`push`) — never whether it's stored.
  * Preferences are a JSONB map type -> {"push": bool, "show": bool}; any missing
    type defaults to {"push": True, "show": True}, so new types are on by default
    with no migration/backfill.
  * create_notification is sync (called inside existing request handlers, same
    db session/transaction). FCM fan-out is a TODO hook at the end — when added it
    reads the same `push` flag computed here.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification_model import (
    Notification,
    NotificationPreference,
    NotificationType,
    NotificationTarget,
    VendorNotificationMute
)
from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationOut,
    NotificationPage,
    TypePref,
)

# Default when a user hasn't set a preference for a type.
DEFAULT_PREF = {"push": True, "show": True}

def _enqueue_push(*, recipient_user_id, ntype, actor_name, preview,
                  target_type, target_id) -> None:
    """
    Fire-and-forget: enqueue an arq job to deliver this notification as a push to
    the recipient's devices. Never raises into the caller — a push enqueue failure
    must not break notification creation.
    """
    try:
        from app.services import queue
        queue.enqueue_push_sync(
            str(recipient_user_id), ntype, actor_name, preview,
            target_type, target_id,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).warning("push enqueue failed", exc_info=True)

# ── Preferences ───────────────────────────────────────────────────────────────

def _raw_prefs(db: Session, user_id: UUID) -> dict:
    """The user's stored prefs dict (may be partial / empty). No defaults filled."""
    row = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    return dict(row.prefs) if row and row.prefs else {}


def effective_pref(db: Session, user_id: UUID, ntype: str) -> dict:
    """The resolved {"push","show"} for one type, defaults filled."""
    stored = _raw_prefs(db, user_id).get(ntype) or {}
    return {
        "push": stored.get("push", DEFAULT_PREF["push"]),
        "show": stored.get("show", DEFAULT_PREF["show"]),
    }


def get_preferences(db: Session, user_id: UUID) -> Dict[str, TypePref]:
    """Full effective map: EVERY known type present, defaults filled in."""
    stored = _raw_prefs(db, user_id)
    out: Dict[str, TypePref] = {}
    for t in NotificationType.ALL:
        s = stored.get(t) or {}
        out[t] = TypePref(
            push=s.get("push", DEFAULT_PREF["push"]),
            show=s.get("show", DEFAULT_PREF["show"]),
        )
    return out


def update_preferences(
    db: Session, user_id: UUID, updates: Dict[str, TypePref]
) -> Dict[str, TypePref]:
    """
    Partial update: merge the given types into the stored map, leave others as-is.
    Creates the prefs row if absent. Returns the full effective map.
    """
    row = (
        db.query(NotificationPreference)
        .filter(NotificationPreference.user_id == user_id)
        .first()
    )
    if row is None:
        row = NotificationPreference(user_id=user_id, prefs={})
        db.add(row)

    merged = dict(row.prefs) if row.prefs else {}
    for t, pref in updates.items():
        # Only accept known types; ignore unknown keys silently.
        if t in NotificationType.ALL:
            merged[t] = {"push": bool(pref.push), "show": bool(pref.show)}

    row.prefs = merged
    # JSONB in-place dict mutation isn't tracked; reassigning the attribute is, but
    # to be safe flag it modified.
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(row, "prefs")
    db.commit()
    return get_preferences(db, user_id)


# ── Per-vendor mute (per-type) ────────────────────────────────────────────────

def is_vendor_muted(db: Session, user_id: UUID, vendor_id, ntype: str) -> bool:
    """True if this user has muted this vendor for this notification type."""
    if vendor_id is None:
        return False
    row = (
        db.query(VendorNotificationMute.user_id)
        .filter(
            VendorNotificationMute.user_id == user_id,
            VendorNotificationMute.vendor_id == vendor_id,
            VendorNotificationMute.type == ntype,
        )
        .first()
    )
    return row is not None


def muted_user_ids(db: Session, vendor_id, ntype: str, candidate_user_ids) -> set:
    """
    Bulk: of `candidate_user_ids`, which have muted this vendor for this type?
    One query — used by the fan-out to hide notifications for muted followers.
    """
    if not candidate_user_ids:
        return set()
    rows = (
        db.query(VendorNotificationMute.user_id)
        .filter(
            VendorNotificationMute.vendor_id == vendor_id,
            VendorNotificationMute.type == ntype,
            VendorNotificationMute.user_id.in_(candidate_user_ids),
        )
        .all()
    )
    return {r[0] for r in rows}


def set_vendor_mute(db: Session, user_id: UUID, vendor_id, ntype: str, muted: bool) -> bool:
    """
    Mute (muted=True) or unmute (muted=False) a vendor for one type. Idempotent.
    Returns the resulting muted state.
    """
    if ntype not in NotificationType.ALL:
        raise ValueError(f"Unknown notification type: {ntype}")

    existing = (
        db.query(VendorNotificationMute)
        .filter(
            VendorNotificationMute.user_id == user_id,
            VendorNotificationMute.vendor_id == vendor_id,
            VendorNotificationMute.type == ntype,
        )
        .first()
    )
    if muted and existing is None:
        db.add(VendorNotificationMute(user_id=user_id, vendor_id=vendor_id, type=ntype))
        db.commit()
    elif not muted and existing is not None:
        db.delete(existing)
        db.commit()
    return muted


def list_vendor_mutes(db: Session, user_id: UUID, vendor_id) -> list:
    """The notification types this user has muted for this vendor."""
    rows = (
        db.query(VendorNotificationMute.type)
        .filter(
            VendorNotificationMute.user_id == user_id,
            VendorNotificationMute.vendor_id == vendor_id,
        )
        .all()
    )
    return [r[0] for r in rows]


def _derive_vendor_id(db: Session, target_type: Optional[str], target_id) -> Optional[object]:
    """
    Best-effort: figure out which vendor a notification is 'about' from its target,
    so the mute can be checked even when the caller didn't pass vendor_id.
      SERVICE  -> the post's vendor (Service.add_vendor_id)
      OFFERING -> the offering's vendor (Add_Service.vendor_id)
      VENDOR   -> the target IS the vendor
    """
    if target_id is None:
        return None
    try:
        if target_type == NotificationTarget.VENDOR:
            return target_id
        if target_type == NotificationTarget.SERVICE:
            from app.models.service_model import Service
            row = db.query(Service.add_vendor_id).filter(Service.id == target_id).first()
            return row[0] if row else None
        if target_type == NotificationTarget.OFFERING:
            from app.models.service_model import Add_Service
            row = db.query(Add_Service.vendor_id).filter(Add_Service.id == target_id).first()
            return row[0] if row else None
    except Exception:
        return None
    return None


# ── Creation (called by every feature) ────────────────────────────────────────

def create_notification(
    db: Session,
    payload: NotificationCreate,
    *,
    vendor_id=None,
    commit: bool = True,
) -> Optional[Notification]:
    """
    Persist a notification for `payload.recipient_user_id`. Always stores the row;
    sets show_in_feed from the user's 'show' preference for this type — UNLESS the
    recipient has muted the vendor this notification is about, in which case the row
    is stored hidden (show_in_feed=False) and not pushed.

    vendor_id: the vendor this notification is 'about'. If None, we try to derive it
    from target_type+target_id (SERVICE/OFFERING/VENDOR). If neither yields a
    vendor, no mute applies.

    Pass commit=False to enlist in the caller's transaction (the caller commits).
    """
    # Don't notify yourself (e.g. liking your own post, messaging in a convo you own).
    if payload.actor_user_id is not None and payload.actor_user_id == payload.recipient_user_id:
        return None

    pref = effective_pref(db, payload.recipient_user_id, payload.type)

    # Per-vendor mute: figure out which vendor this is about, then check the mute.
    about_vendor = vendor_id if vendor_id is not None else _derive_vendor_id(
        db, payload.target_type, payload.target_id
    )
    muted = is_vendor_muted(db, payload.recipient_user_id, about_vendor, payload.type)

    show = bool(pref["show"]) and not muted   # muted -> stored but hidden

    notif = Notification(
        recipient_user_id=payload.recipient_user_id,
        type=payload.type,
        actor_user_id=payload.actor_user_id,
        actor_name=payload.actor_name,
        target_type=payload.target_type,
        target_id=payload.target_id,
        preview=payload.preview,
        show_in_feed=show,
        read_at=None,
    )
    db.add(notif)

    if commit:
        db.commit()
        db.refresh(notif)

    # ── FCM hook (later) ──────────────────────────────────────────────────────
    # push = bool(pref["push"]) and not muted
    # if push:
    #     enqueue_push(notif)   # device-token lookup + FCM send, added in the push phase
    return notif


def notify(
    db: Session,
    *,
    recipient_user_id: UUID,
    type: str,
    actor_user_id: Optional[UUID] = None,
    actor_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    preview: Optional[str] = None,
    vendor_id=None,
    commit: bool = True,
) -> Optional[Notification]:
    """Convenience wrapper so feature code reads cleanly:

        notify(db, recipient_user_id=owner_id, type=NotificationType.LIKE,
               actor_user_id=me.id, actor_name=my_name,
               target_type=NotificationTarget.SERVICE, target_id=str(service_id))
    """
    return create_notification(
        db,
        NotificationCreate(
            recipient_user_id=recipient_user_id,
            type=type,
            actor_user_id=actor_user_id,
            actor_name=actor_name,
            target_type=target_type,
            target_id=target_id,
            preview=preview,
        ),
        vendor_id=vendor_id,
        commit=commit,
    )


# ── Reads / list / mark-read ──────────────────────────────────────────────────

def _to_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id,
        type=n.type,
        actor_user_id=n.actor_user_id,
        actor_name=n.actor_name,
        target_type=n.target_type,
        target_id=n.target_id,
        preview=n.preview,
        is_read=n.read_at is not None,
        created_at=n.created_at,
    )


def unread_count(db: Session, user_id: UUID) -> int:
    return (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == user_id,
            Notification.read_at.is_(None),
            Notification.show_in_feed.is_(True),
        )
        .count()
    )


def list_notifications(
    db: Session,
    user_id: UUID,
    *,
    limit: int = 30,
    cursor: Optional[str] = None,
) -> NotificationPage:
    """
    Keyset pagination by updated_at (newest first), so coalesced message
    notifications float to the top. `cursor` is the ISO updated_at of the last item
    from the previous page; pass it to get the next page. Only
    rows with show_in_feed=True are returned (hidden ones stay saved but unseen).
    """
    q = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == user_id,
            Notification.show_in_feed.is_(True),
        )
    )
    if cursor:
        try:
            cur_dt = datetime.fromisoformat(cursor)
            q = q.filter(Notification.updated_at < cur_dt)
        except ValueError:
            pass

    rows = (
        q.order_by(Notification.updated_at.desc())
        .limit(limit + 1)
        .all()
    )

    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = page[-1].updated_at.isoformat() if (has_more and page) else None

    return NotificationPage(
        items=[_to_out(n) for n in page],
        next_cursor=next_cursor,
        unread_count=unread_count(db, user_id),
    )


def mark_read(db: Session, user_id: UUID, notification_id: UUID) -> int:
    """Mark one notification read (idempotent). Returns the new unread count."""
    n = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
        )
        .first()
    )
    if n is not None and n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
    return unread_count(db, user_id)


def mark_all_read(db: Session, user_id: UUID) -> int:
    """Mark all of the user's unread notifications read. Returns new unread (0)."""
    db.query(Notification).filter(
        Notification.recipient_user_id == user_id,
        Notification.read_at.is_(None),
    ).update(
        {Notification.read_at: datetime.now(timezone.utc)},
        synchronize_session=False,
    )
    db.commit()
    return unread_count(db, user_id)


# ── Coalesced message notification (called by chat_ws.publish_new_message) ────

def notify_message(
    db: Session,
    *,
    recipient_user_id: UUID,
    conversation_id,
    actor_user_id: Optional[UUID] = None,
    actor_name: Optional[str] = None,
    preview: Optional[str] = None,
    commit: bool = True,
) -> Optional[Notification]:
    """
    Coalesced message notification: at most ONE unread MESSAGE notification per
    (recipient, conversation). If an unread one exists, update its preview/actor
    (updated_at auto-bumps -> floats to top); else create a new one.

    Coalescing key: type=MESSAGE, target_id=conversation_id, read_at IS NULL.
    """
    if actor_user_id is not None and actor_user_id == recipient_user_id:
        return None

    convo_key = str(conversation_id)

    existing = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == recipient_user_id,
            Notification.type == NotificationType.MESSAGE,
            Notification.target_id == convo_key,
            Notification.read_at.is_(None),
        )
        .order_by(Notification.updated_at.desc())
        .first()
    )

    if existing is not None:
        existing.actor_user_id = actor_user_id
        existing.actor_name = actor_name
        existing.preview = preview
        # updated_at bumps automatically via TimestampMixin.onupdate.
        if commit:
            db.commit()
            db.refresh(existing)
        return existing

    pref = effective_pref(db, recipient_user_id, NotificationType.MESSAGE)
    notif = Notification(
        recipient_user_id=recipient_user_id,
        type=NotificationType.MESSAGE,
        actor_user_id=actor_user_id,
        actor_name=actor_name,
        target_type=NotificationTarget.CONVERSATION,
        target_id=convo_key,
        preview=preview,
        show_in_feed=bool(pref["show"]),
        read_at=None,
    )
    db.add(notif)
    if commit:
        db.commit()
        db.refresh(notif)
    # TODO FCM hook (later): if pref["push"]: enqueue_push(notif)
    return notif


# ── Recipient resolution helpers (shared by social-event wiring) ──────────────

def vendor_owner_user_id(db: Session, vendor_id) -> Optional[UUID]:
    """A vendor -> its owning user's id (Vendor.user_id)."""
    from app.models.vendor_model import Vendor
    v = db.query(Vendor.user_id).filter(Vendor.vendor_id == vendor_id).first()
    return v[0] if v else None


def service_owner_user_id(db: Session, service_id) -> Optional[UUID]:
    """A service -> its vendor -> that vendor's owning user id (the post owner)."""
    from app.models.service_model import Service
    from app.models.vendor_model import Vendor
    row = (
        db.query(Vendor.user_id)
        .join(Service, Service.add_vendor_id == Vendor.vendor_id)
        .filter(Service.id == service_id)
        .first()
    )
    return row[0] if row else None


# ── New-service follower fan-out (called by the arq worker) ───────────────────

def fanout_new_service(
    db: Session,
    *,
    target_id,
    vendor_id,
    is_big: bool = False,
    target_type: Optional[str] = None,
    actor_name: Optional[str] = None,
    preview: Optional[str] = None,
) -> int:
    """
    Fan a new-service event out to ALL followers of `vendor_id`. Bulk + batched:

      1. Load every follower of the vendor (customers and vendors).
      2. Resolve each to its owning USER id (customer.user_id / Vendor.user_id),
         in two batched queries — notifications are keyed by user id.
      3. Exclude the posting vendor's own owner (no self-notify).
      4. Batch-load notification_preferences for all recipients in ONE query to
         decide show_in_feed per row (missing -> default show=True).
      5. Bulk-insert the rows in a single commit.

    Returns the number of notifications created. Designed to run in the worker
    (its own DB session), not inside the create-service request.
    """
    from app.models.social_model import Following
    from app.models.customer_model import customer as CustomerModel
    from app.models.vendor_model import Vendor

    ntype = NotificationType.BIG_SERVICE if is_big else NotificationType.NEW_SERVICE
    # Posts (Service) target SERVICE; offerings (Add_Service) target OFFERING.
    if target_type is None:
        target_type = NotificationTarget.SERVICE if is_big else NotificationTarget.OFFERING

    # 1. Followers of this vendor.
    follows = (
        db.query(Following.follower_customer_id, Following.follower_vendor_id)
        .filter(Following.vendor_id == vendor_id)
        .all()
    )
    if not follows:
        return 0

    customer_ids = {fc for (fc, fv) in follows if fc is not None}
    vendor_ids = {fv for (fc, fv) in follows if fv is not None}

    # 2. Resolve follower actor ids -> owning user ids (batched).
    recipient_user_ids: set = set()

    if customer_ids:
        rows = (
            db.query(CustomerModel.user_id)
            .filter(CustomerModel.customer_id.in_(customer_ids))
            .all()
        )
        recipient_user_ids.update(r[0] for r in rows if r[0] is not None)

    if vendor_ids:
        rows = (
            db.query(Vendor.user_id)
            .filter(Vendor.vendor_id.in_(vendor_ids))
            .all()
        )
        recipient_user_ids.update(r[0] for r in rows if r[0] is not None)

    # 3. Exclude the posting vendor's own owner.
    poster_owner = vendor_owner_user_id(db, vendor_id)
    if poster_owner is not None:
        recipient_user_ids.discard(poster_owner)

    if not recipient_user_ids:
        return 0

    # 4. Batch-load prefs to decide show_in_feed (and later, push) per recipient.
    pref_rows = (
        db.query(NotificationPreference.user_id, NotificationPreference.prefs)
        .filter(NotificationPreference.user_id.in_(recipient_user_ids))
        .all()
    )
    prefs_by_user = {uid: (p or {}) for (uid, p) in pref_rows}

    # Per-vendor mute (bulk): which recipients muted THIS vendor for THIS type?
    # Muted -> stored but hidden (show_in_feed=False), consistent with create_notification.
    muted = muted_user_ids(db, vendor_id, ntype, recipient_user_ids)

    def _show_for(uid) -> bool:
        if uid in muted:
            return False
        type_pref = (prefs_by_user.get(uid) or {}).get(ntype) or {}
        return bool(type_pref.get("show", DEFAULT_PREF["show"]))

    # 5. Bulk insert.
    target_key = str(target_id)
    now = datetime.now(timezone.utc)
    mappings = []
    import uuid as _uuid
    for uid in recipient_user_ids:
        mappings.append({
            "id": _uuid.uuid4(),
            "recipient_user_id": uid,
            "type": ntype,
            "actor_user_id": poster_owner,
            "actor_name": actor_name,
            "target_type": target_type,
            "target_id": target_key,
            "preview": preview or ("posted a new service"),
            "show_in_feed": _show_for(uid),
            "read_at": None,
            "created_at": now,
            "updated_at": now,
        })

    db.bulk_insert_mappings(Notification, mappings)
    db.commit()

    # ── FCM hook (later) ──────────────────────────────────────────────────────
    # For recipients whose prefs_by_user[uid][ntype].push is True, enqueue pushes.
    return len(mappings)

# ── Booking party resolution ──────────────────────────────────────────────────
 
def booking_parties(db: Session, booking_id) -> dict:
    """
    Resolve both parties + the vendor for a booking, for notification wiring:
      {
        "customer_user_id": <Booking.user_id>,
        "vendor_id":        <the service's vendor>,
        "vendor_user_id":   <Vendor.user_id, the owner>,
        "service_id":       <Booking.service_id>,
      }
    Returns {} if the booking can't be resolved.
    """
    from app.models.booking_model import Booking
    from app.models.service_model import Service
    from app.models.vendor_model import Vendor
 
    row = (
        db.query(Booking.user_id, Booking.service_id, Vendor.vendor_id, Vendor.user_id)
        .join(Service, Booking.service_id == Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .filter(Booking.booking_id == booking_id)
        .first()
    )
    if not row:
        return {}
    customer_user_id, service_id, vendor_id, vendor_user_id = row
    return {
        "customer_user_id": customer_user_id,
        "vendor_id": vendor_id,
        "vendor_user_id": vendor_user_id,
        "service_id": service_id,
    }