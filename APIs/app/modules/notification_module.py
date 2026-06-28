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
    NotificationTarget
)
from app.schemas.notification_schema import (
    NotificationCreate,
    NotificationOut,
    NotificationPage,
    TypePref,
)

# Default when a user hasn't set a preference for a type.
DEFAULT_PREF = {"push": True, "show": True}


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


# ── Creation (called by every feature) ────────────────────────────────────────

def create_notification(
    db: Session,
    payload: NotificationCreate,
    *,
    commit: bool = True,
) -> Optional[Notification]:
    """
    Persist a notification for `payload.recipient_user_id`. Always stores the row;
    sets show_in_feed from the user's 'show' preference for this type. Returns the
    created Notification, or None if it was suppressed (see self-notify guard).

    Pass commit=False to enlist in the caller's transaction (the caller commits).
    """
    # Don't notify yourself (e.g. liking your own post, messaging in a convo you own).
    if payload.actor_user_id is not None and payload.actor_user_id == payload.recipient_user_id:
        return None

    pref = effective_pref(db, payload.recipient_user_id, payload.type)

    notif = Notification(
        recipient_user_id=payload.recipient_user_id,
        type=payload.type,
        actor_user_id=payload.actor_user_id,
        actor_name=payload.actor_name,
        target_type=payload.target_type,
        target_id=payload.target_id,
        preview=payload.preview,
        show_in_feed=bool(pref["show"]),
        read_at=None,
    )
    db.add(notif)

    if commit:
        db.commit()
        db.refresh(notif)

    # ── FCM hook (later) ──────────────────────────────────────────────────────
    # if pref["push"]:
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

# ------------------ SPecial notifs
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
    # FCM hook (later): if pref["push"]: enqueue_push(notif)
    return notif