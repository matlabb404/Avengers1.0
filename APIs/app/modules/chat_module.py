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


def _human_size(n: Optional[int]) -> Optional[str]:
    """Bytes -> '2.4 MB'. Returns None for unknown/zero so the client can hide it."""
    if not n or n <= 0:
        return None
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _asset_to_attachment(asset) -> dict:
    """Shape a MediaAsset into an AttachmentOut dict (kind/url/name/size)."""
    kind = asset.kind.value.upper() if hasattr(asset.kind, "value") else str(asset.kind).upper()
    deriv = asset.derivatives or {}
    # Video shows its poster; image/file use the original object URL.
    url = (deriv.get("thumbnail") or asset.original_url) if kind == "VIDEO" else asset.original_url
    return {
        "kind": kind,
        "url": url,
        "name": getattr(asset, "filename", None),
        "size": _human_size(getattr(asset, "actual_size", None) or getattr(asset, "declared_size", None)),
    }


def _resolve_attachments(db: Session, m) -> list[dict]:
    """Ordered attachments for a message. Prefers the message_attachments rows;
       falls back to the legacy single asset_id so old messages still render."""
    from app.models.media_model import MediaAsset

    rows = list(getattr(m, "attachments", None) or [])
    if rows:
        ordered_ids = [r.asset_id for r in sorted(rows, key=lambda r: r.position)]
        by_id = {a.id: a for a in db.query(MediaAsset).filter(MediaAsset.id.in_(ordered_ids)).all()}
        return [_asset_to_attachment(by_id[aid]) for aid in ordered_ids if aid in by_id]

    if m.asset_id:
        a = db.query(MediaAsset).filter(MediaAsset.id == m.asset_id).first()
        if a is not None:
            return [_asset_to_attachment(a)]
    return []


def _format_duration(mins: Optional[int]) -> Optional[str]:
    if not mins or mins <= 0:
        return None
    if mins < 60:
        return f"{mins} min"
    h, m = divmod(mins, 60)
    return f"{h}h" if m == 0 else f"{h}h {m}m"


def _resolve_shared_post(db: Session, shared_service_id: Optional[UUID]) -> Optional[dict]:
    """Flatten a shared service/post into the boarding-pass payload."""
    if shared_service_id is None:
        return None
    from app.models.service_model import Service, Add_Service, price_history
    from app.models.media_model import MediaAsset

    row = (
        db.query(Service, Add_Service, price_history)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .outerjoin(price_history, Service.price_history == price_history.id)
        .filter(Service.id == shared_service_id)
        .first()
    )
    if row is None:
        return None
    service, add_service, ph = row

    price_label = None
    if ph is not None and ph.price_minor is not None:
        from app.utils.money import format_money
        price_label = format_money(ph.price_minor, ph.currency)
    elif service.price is not None:
        price_label = f"GH¢ {service.price:,.2f}"

    thumbnail_url = None
    if service.asset_ids:
        a = db.query(MediaAsset).filter(MediaAsset.id == service.asset_ids[0]).first()
        if a is not None:
            deriv = a.derivatives or {}
            thumbnail_url = deriv.get("thumbnail") or a.original_url

    return {
        "post_id": service.id,
        "service": add_service.service_name,
        "price_label": price_label,
        "duration_label": _format_duration(add_service.interval_minutes),
        "thumbnail_url": thumbnail_url,
    }


def _message_out(db: Session, m) -> dict:
    """Shape a Message row into the MessageOut dict (resolving attachments,
       shared-post payload, and the reply-to id)."""
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "sender_role": m.sender_role,
        "kind": m.kind,
        "body": m.body,
        "asset_id": m.asset_id,
        "asset_url": _resolve_asset_url(db, m.asset_id),
        "shared_service_id": m.shared_service_id,
        "attachments": _resolve_attachments(db, m),
        "shared_post": _resolve_shared_post(db, m.shared_service_id),
        "reply_to": m.reply_to_message_id,
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
    asset_ids: Optional[list[UUID]] = None,
    shared_service_id: Optional[UUID] = None,
    reply_to_message_id: Optional[UUID] = None,
) -> dict:
    """
    Persist a message, update the conversation's denormalized preview + the OTHER
    side's unread counter, all in one transaction. Returns the MessageOut dict.
    The router/WS layer then publishes it live.
    """
    from app.models.chat_model import (
        Conversation, Message, MessageAttachment, MessageKind, SenderRole,
    )

    convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    _assert_participant(convo, requester_user_id, requester_vendor_id, sender_role)

    # Normalize the attachment list: explicit asset_ids win; else fold in the
    # legacy singular asset_id. De-dupe while preserving order.
    raw_ids = list(asset_ids) if asset_ids else ([asset_id] if asset_id else [])
    seen: set = set()
    ids: list[UUID] = []
    for aid in raw_ids:
        if aid is not None and aid not in seen:
            seen.add(aid)
            ids.append(aid)

    # Validate content by kind.
    k = MessageKind(kind)
    if k == MessageKind.TEXT and not (body and body.strip()):
        raise HTTPException(status_code=400, detail="Text message requires body")
    if k == MessageKind.IMAGE and not ids:
        raise HTTPException(status_code=400, detail="Image message requires at least one asset")
    if k == MessageKind.POST_SHARE and shared_service_id is None:
        raise HTTPException(status_code=400, detail="Post share requires shared_service_id")

    # Reply target must be a real message in THIS conversation (ignore otherwise,
    # rather than failing the send — the quote is cosmetic).
    reply_id = None
    if reply_to_message_id is not None:
        parent = (
            db.query(Message)
            .filter(Message.id == reply_to_message_id,
                    Message.conversation_id == conversation_id)
            .first()
        )
        reply_id = parent.id if parent is not None else None

    msg = Message(
        conversation_id=conversation_id,
        sender_role=SenderRole(sender_role),
        kind=k,
        body=body,
        asset_id=ids[0] if ids else None,          # legacy pointer = first attachment
        shared_service_id=shared_service_id,
        reply_to_message_id=reply_id,
    )
    db.add(msg)
    db.flush()                                      # need msg.id for attachment rows

    for pos, aid in enumerate(ids):
        db.add(MessageAttachment(message_id=msg.id, asset_id=aid, position=pos))

    # Denormalized preview + unread bump for the recipient side.
    preview = _preview_for(db, k, body, ids)
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


def _preview_for(db: Session, kind, body: Optional[str], asset_ids: Optional[list[UUID]] = None) -> str:
    from app.models.chat_model import MessageKind
    from app.models.media_model import MediaAsset, MediaKind

    text = (body or "").strip().replace("\n", " ")

    if asset_ids:
        assets = db.query(MediaAsset).filter(MediaAsset.id.in_(asset_ids)).all()
        n_media = sum(1 for a in assets if a.kind in (MediaKind.IMAGE, MediaKind.VIDEO))
        n_file = sum(1 for a in assets if a.kind == MediaKind.FILE)
        if n_media and not n_file:
            label = "📷 Photo" if n_media == 1 else f"📷 {n_media} photos"
        elif n_file and not n_media:
            label = "📎 Attachment" if n_file == 1 else f"📎 {n_file} files"
        else:
            label = f"📎 {n_media + n_file} attachments"
        return f"{label} · {text[:40]}" if text else label

    if kind == MessageKind.POST_SHARE:
        return "🔗 Shared a post"

    return (text[:80] + "…") if len(text) > 80 else text