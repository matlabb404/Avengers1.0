"""
Delivery model is persist-then-push: these functions PERSIST (and return the saved
message/conversation). The WS layer calls publish_message() to push live; if no
socket is connected, the data is still safe in Postgres for the next fetch.
"""

import base64
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session


# ── cursor helpers (created_at, id) ──────────────────────────────────────────

def _encode_cursor(ts: datetime, mid: UUID) -> str:
    return base64.urlsafe_b64encode(f"{ts.isoformat()}|{mid}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, str]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_s, mid = raw.split("|", 1)
    return datetime.fromisoformat(ts_s), mid


# ── media / share resolution ─────────────────────────────────────────────────

def _resolve_asset_url(db: Session, asset_id: Optional[UUID]) -> Optional[str]:
    if asset_id is None:
        return None
    from app.models.media_model import MediaAsset
    a = db.query(MediaAsset).filter(MediaAsset.id == asset_id).first()
    if a is None:
        return None
    # Prefer the poster for videos, else the original.
    deriv = a.derivatives or {}
    return deriv.get("thumbnail") or a.original_url


def _message_out(db: Session, m) -> dict:
    """Shape a Message row into the MessageOut dict (resolving asset_url)."""
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "sender_role": m.sender_role,
        "kind": m.kind,
        "body": m.body,
        "asset_id": m.asset_id,
        "asset_url": _resolve_asset_url(db, m.asset_id),
        "shared_service_id": m.shared_service_id,
        "read_at": m.read_at,
        "created_at": m.created_at,
    }


# ── conversations ─────────────────────────────────────────────────────────────

def open_conversation(db: Session, customer_user_id: UUID, vendor_id: UUID):
    """Get-or-create the 1-on-1 thread for (customer, vendor). Idempotent."""
    from app.models.chat_model import Conversation

    convo = (
        db.query(Conversation)
        .filter(
            Conversation.customer_user_id == customer_user_id,
            Conversation.vendor_id == vendor_id,
        )
        .first()
    )
    if convo is None:
        convo = Conversation(customer_user_id=customer_user_id, vendor_id=vendor_id)
        db.add(convo)
        db.commit()
        db.refresh(convo)
    return convo


def _counterparty(db: Session, convo, role: str) -> tuple[Optional[str], Optional[str]]:
    """(name, avatar_url) of the OTHER side, from the requester's perspective."""
    from app.models.vendor_model import Vendor
    from app.models.account_model import User  # adjust if your user model differs

    if role == "CUSTOMER":
        # other side = the vendor (business)
        v = db.query(Vendor).filter(Vendor.vendor_id == convo.vendor_id).first()
        name = (v.business_name if v and v.business_name else None) or (
            f"{v.first_name or ''} {v.last_name or ''}".strip() if v else None
        )
        return (name or "Vendor", None)
    else:
        # other side = the customer (user)
        u = db.query(User).filter(User.id == convo.customer_user_id).first()
        name = None
        if u is not None:
            name = getattr(u, "first_name", None) or getattr(u, "username", None) or getattr(u, "email", None)
        return (name or "Customer", None)


def list_conversations(
    db: Session,
    requester_user_id: UUID,
    requester_vendor_id: Optional[UUID],
    role: str,
    limit: int = 30,
    cursor: Optional[str] = None,
) -> dict:
    """Inbox for the requester. CUSTOMER sees threads where they're the customer;
       VENDOR sees threads where they're the vendor."""
    from app.models.chat_model import Conversation

    q = db.query(Conversation)
    if role == "CUSTOMER":
        q = q.filter(Conversation.customer_user_id == requester_user_id)
    else:
        if requester_vendor_id is None:
            raise HTTPException(status_code=400, detail="Vendor identity required")
        q = q.filter(Conversation.vendor_id == requester_vendor_id)

    # newest activity first; keyset on (last_message_at, id)
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Conversation.last_message_at < c_ts,
                and_(Conversation.last_message_at == c_ts, Conversation.id < c_id),
            )
        )
    q = q.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
    rows = q.limit(limit + 1).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for convo in rows:
        name, avatar = _counterparty(db, convo, role)
        unread = convo.customer_unread if role == "CUSTOMER" else convo.vendor_unread
        items.append({
            "id": convo.id,
            "vendor_id": convo.vendor_id,
            "customer_user_id": convo.customer_user_id,
            "counterparty_name": name,
            "counterparty_avatar_url": avatar,
            "last_message_preview": convo.last_message_preview,
            "last_message_at": convo.last_message_at,
            "last_sender_role": convo.last_sender_role,
            "unread_count": unread or 0,
            "created_at": convo.created_at,
        })

    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        if last.last_message_at is not None:
            next_cursor = _encode_cursor(last.last_message_at, last.id)

    return {"items": items, "next_cursor": next_cursor}


# ── messages ──────────────────────────────────────────────────────────────────

def get_messages(
    db: Session,
    conversation_id: UUID,
    requester_user_id: UUID,
    requester_vendor_id: Optional[UUID],
    role: str,
    limit: int = 30,
    cursor: Optional[str] = None,
) -> dict:
    """Paginate a thread, newest first. Verifies the requester is a participant."""
    from app.models.chat_model import Conversation, Message

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_participant(convo, requester_user_id, requester_vendor_id, role)

    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Message.created_at < c_ts,
                and_(Message.created_at == c_ts, Message.id < c_id),
            )
        )
    q = q.order_by(Message.created_at.desc(), Message.id.desc())
    rows = q.limit(limit + 1).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = [_message_out(db, m) for m in rows]
    next_cursor = None
    if has_more and rows:
        last = rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return {"items": items, "next_cursor": next_cursor}


def send_message(
    db: Session,
    conversation_id: UUID,
    sender_role: str,            # "CUSTOMER" | "VENDOR"
    requester_user_id: UUID,
    requester_vendor_id: Optional[UUID],
    kind: str = "TEXT",
    body: Optional[str] = None,
    asset_id: Optional[UUID] = None,
    shared_service_id: Optional[UUID] = None,
) -> dict:
    """
    Persist a message, update the conversation's denormalized preview + the OTHER
    side's unread counter, all in one transaction. Returns the MessageOut dict.
    The router/WS layer then publishes it live.
    """
    from app.models.chat_model import Conversation, Message, MessageKind, SenderRole

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_participant(convo, requester_user_id, requester_vendor_id, sender_role)

    # Validate content by kind.
    k = MessageKind(kind)
    if k == MessageKind.TEXT and not (body and body.strip()):
        raise HTTPException(status_code=400, detail="Text message requires body")
    if k == MessageKind.IMAGE and asset_id is None:
        raise HTTPException(status_code=400, detail="Image message requires asset_id")
    if k == MessageKind.POST_SHARE and shared_service_id is None:
        raise HTTPException(status_code=400, detail="Post share requires shared_service_id")

    msg = Message(
        conversation_id=conversation_id,
        sender_role=SenderRole(sender_role),
        kind=k,
        body=body,
        asset_id=asset_id,
        shared_service_id=shared_service_id,
    )
    db.add(msg)

    # Denormalized preview + unread bump for the recipient side.
    preview = _preview_for(k, body)
    convo.last_message_preview = preview
    convo.last_message_at = datetime.now(timezone.utc)
    convo.last_sender_role = SenderRole(sender_role)
    if sender_role == "CUSTOMER":
        convo.vendor_unread = (convo.vendor_unread or 0) + 1
    else:
        convo.customer_unread = (convo.customer_unread or 0) + 1

    db.commit()
    db.refresh(msg)
    return _message_out(db, msg)


def mark_read(
    db: Session,
    conversation_id: UUID,
    reader_role: str,
    requester_user_id: UUID,
    requester_vendor_id: Optional[UUID],
) -> dict:
    """Zero the reader's unread counter and stamp read_at on the other side's
       unread messages. Returns {conversation_id, read_up_to}."""
    from app.models.chat_model import Conversation, Message, SenderRole

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_participant(convo, requester_user_id, requester_vendor_id, reader_role)

    now = datetime.now(timezone.utc)
    # The messages the reader is reading were sent by the OTHER side.
    other = SenderRole.VENDOR if reader_role == "CUSTOMER" else SenderRole.CUSTOMER
    (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.sender_role == other,
            Message.read_at.is_(None),
        )
        .update({Message.read_at: now}, synchronize_session=False)
    )
    if reader_role == "CUSTOMER":
        convo.customer_unread = 0
    else:
        convo.vendor_unread = 0
    db.commit()
    return {"conversation_id": conversation_id, "read_up_to": now}


# ── helpers ───────────────────────────────────────────────────────────────────

def _assert_participant(convo, user_id: UUID, vendor_id: Optional[UUID], role: str):
    if role == "CUSTOMER":
        if convo.customer_user_id != user_id:
            raise HTTPException(status_code=403, detail="Not a participant")
    elif role == "VENDOR":
        if vendor_id is None or convo.vendor_id != vendor_id:
            raise HTTPException(status_code=403, detail="Not a participant")
    else:
        raise HTTPException(status_code=400, detail="Invalid role")


def _preview_for(kind, body: Optional[str]) -> str:
    from app.models.chat_model import MessageKind
    if kind == MessageKind.IMAGE:
        return "📷 Photo"
    if kind == MessageKind.POST_SHARE:
        return "🔗 Shared a post"
    text = (body or "").strip().replace("\n", " ")
    return (text[:80] + "…") if len(text) > 80 else text