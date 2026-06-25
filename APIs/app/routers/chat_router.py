from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.modules import chat_module
from app.schemas.chat_schema import (
    ConversationList,
    ConversationOut,
    MessagePage,
    MessageOut,
    OpenConversationRequest,
    SendMessageRequest,
)
from app.modules.account_module import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ASSUMPTION #2: user -> vendor mapping ─────────────────────────────────────
def _resolve_vendor_id(db: Session, user_id: UUID) -> Optional[UUID]:
    """The caller's vendor_id, if they own a vendor. None for pure customers."""
    from app.models.vendor_model import Vendor
    v = db.query(Vendor).filter(Vendor.user_id == user_id).first()
    return v.vendor_id if v else None


def _role(role: str) -> str:
    r = (role or "CUSTOMER").upper()
    return r if r in ("CUSTOMER", "VENDOR") else "CUSTOMER"


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/conversations", response_model=ConversationOut)
def open_conversation(
    payload: OpenConversationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Open (or get) the 1-on-1 thread between the current user (customer) and a
       vendor. The customer is always the authenticated user here."""
    convo = chat_module.open_conversation(
        db, customer_user_id=current_user.id, vendor_id=payload.vendor_id
    )
    name, avatar = chat_module._counterparty(db, convo, "CUSTOMER")
    return ConversationOut(
        id=convo.id,
        vendor_id=convo.vendor_id,
        customer_user_id=convo.customer_user_id,
        counterparty_name=name,
        counterparty_avatar_url=avatar,
        last_message_preview=convo.last_message_preview,
        last_message_at=convo.last_message_at,
        last_sender_role=convo.last_sender_role,
        unread_count=convo.customer_unread or 0,
        created_at=convo.created_at,
    )


@router.get("/conversations", response_model=ConversationList)
def list_conversations(
    role: str = Query("CUSTOMER", pattern="^(?i)(customer|vendor)$"),
    limit: int = Query(30, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Inbox. role=CUSTOMER -> threads where I'm the shopper; role=VENDOR ->
       threads where I'm the business."""
    r = _role(role)
    vendor_id = _resolve_vendor_id(db, current_user.id) if r == "VENDOR" else None
    result = chat_module.list_conversations(
        db,
        requester_user_id=current_user.id,
        requester_vendor_id=vendor_id,
        role=r,
        limit=limit,
        cursor=cursor,
    )
    return ConversationList(
        items=[ConversationOut(**c) for c in result["items"]],
        next_cursor=result["next_cursor"],
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessagePage)
def get_messages(
    conversation_id: UUID,
    role: str = Query("CUSTOMER", pattern="^(?i)(customer|vendor)$"),
    limit: int = Query(30, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = _role(role)
    vendor_id = _resolve_vendor_id(db, current_user.id) if r == "VENDOR" else None
    result = chat_module.get_messages(
        db,
        conversation_id=conversation_id,
        requester_user_id=current_user.id,
        requester_vendor_id=vendor_id,
        role=r,
        limit=limit,
        cursor=cursor,
    )
    return MessagePage(
        items=[MessageOut(**m) for m in result["items"]],
        next_cursor=result["next_cursor"],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageOut)
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    role: str = Query("CUSTOMER", pattern="^(?i)(customer|vendor)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Persist a message, then push it live over WS to the recipient (if online)."""
    r = _role(role)
    vendor_id = _resolve_vendor_id(db, current_user.id) if r == "VENDOR" else None
    out = chat_module.send_message(
        db,
        conversation_id=conversation_id,
        sender_role=r,
        requester_user_id=current_user.id,
        requester_vendor_id=vendor_id,
        kind=payload.kind.value if hasattr(payload.kind, "value") else str(payload.kind),
        body=payload.body,
        asset_id=payload.asset_id,
        shared_service_id=payload.shared_service_id,
    )
    # Push live (no-op if recipient isn't connected). Imported here to avoid a
    # circular import at module load; the WS layer is file #4.
    try:
        from app.realtime.chat_ws import publish_new_message
        await publish_new_message(db, conversation_id=conversation_id, message=out)
    except Exception:
        # Delivery is best-effort; the message is already persisted.
        pass
    return MessageOut(**out)


@router.post("/conversations/{conversation_id}/read")
def mark_read(
    conversation_id: UUID,
    role: str = Query("CUSTOMER", pattern="^(?i)(customer|vendor)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    r = _role(role)
    vendor_id = _resolve_vendor_id(db, current_user.id) if r == "VENDOR" else None
    return chat_module.mark_read(
        db,
        conversation_id=conversation_id,
        reader_role=r,
        requester_user_id=current_user.id,
        requester_vendor_id=vendor_id,
    )