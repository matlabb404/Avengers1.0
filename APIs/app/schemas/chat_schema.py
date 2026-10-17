from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SenderRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"


class MessageKind(str, Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    POST_SHARE = "POST_SHARE"


# ── Messages ──────────────────────────────────────────────────────────────────

class AttachmentOut(BaseModel):
    """One resolved attachment. `kind` is IMAGE | VIDEO | FILE. For files the
       client shows `name` + `size`; for images it uses `url` directly."""
    kind: str
    url: Optional[str] = None
    name: Optional[str] = None               # file display name (FILE only)
    size: Optional[str] = None               # human-readable, e.g. "2.4 MB"


class SharedPostOut(BaseModel):
    """The post a message privately replies to, flattened for the boarding-pass
       card so the client renders it without a second fetch."""
    post_id: UUID
    service: str
    price_label: Optional[str] = None
    duration_label: Optional[str] = None
    thumbnail_url: Optional[str] = None


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    sender_role: SenderRole
    kind: MessageKind
    body: Optional[str] = None
    asset_id: Optional[UUID] = None          # legacy single-image pointer
    asset_url: Optional[str] = None          # legacy resolved media URL for IMAGE
    shared_service_id: Optional[UUID] = None
    # New, richer shapes the Compose client reads:
    attachments: List[AttachmentOut] = Field(default_factory=list)
    shared_post: Optional[SharedPostOut] = None
    reply_to: Optional[UUID] = None          # id of the quoted message (same thread)
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessagePage(BaseModel):
    items: List[MessageOut] = Field(default_factory=list)
    next_cursor: Optional[str] = None        # opaque (created_at,id) cursor


class SendMessageRequest(BaseModel):
    """Send into a conversation.
       TEXT       -> body
       IMAGE      -> asset_ids (one or more; images and/or files) + optional body caption
       POST_SHARE -> shared_service_id (+ optional body note)
       Any kind may set reply_to_message_id to quote another message in the thread.
       `asset_id` (singular) is kept for older clients; it's folded into asset_ids."""
    kind: MessageKind = MessageKind.TEXT
    body: Optional[str] = None
    asset_id: Optional[UUID] = None                      # legacy single-attachment
    asset_ids: Optional[List[UUID]] = None               # ordered: photos and/or files
    shared_service_id: Optional[UUID] = None
    reply_to_message_id: Optional[UUID] = None


# ── Conversations (inbox) ─────────────────────────────────────────────────────

class ConversationOut(BaseModel):
    id: UUID
    vendor_id: UUID
    customer_user_id: UUID
    # The "other party" as seen by the requester, resolved server-side:
    counterparty_name: Optional[str] = None
    counterparty_avatar_url: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    last_sender_role: Optional[SenderRole] = None
    unread_count: int = 0                     # for the requesting side
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationList(BaseModel):
    items: List[ConversationOut] = Field(default_factory=list)
    next_cursor: Optional[str] = None


class OpenConversationRequest(BaseModel):
    """Open (or create) the 1-on-1 thread with a given vendor. The customer is the
       authenticated user; vendor_id identifies the business."""
    vendor_id: UUID


# ── WebSocket frames ──────────────────────────────────────────────────────────

class WsFrameType(str, Enum):
    MESSAGE = "MESSAGE"          # a new message in a conversation
    READ = "READ"               # the other side read up to a point
    TYPING = "TYPING"           # optional typing indicator
    PING = "PING"
    PONG = "PONG"
    ERROR = "ERROR"


class WsFrame(BaseModel):
    """Envelope for everything sent over the socket, in both directions."""
    type: WsFrameType
    conversation_id: Optional[UUID] = None
    message: Optional[MessageOut] = None
    # For READ receipts:
    read_up_to: Optional[datetime] = None
    reader_role: Optional[SenderRole] = None
    # For TYPING:
    typing_role: Optional[SenderRole] = None
    # For ERROR:
    error: Optional[str] = None