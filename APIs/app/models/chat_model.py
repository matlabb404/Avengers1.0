from app.config.db.postgresql import Base
from app.utils.mixins import TimestampMixin
from sqlalchemy import (
    Column, String, DateTime, Enum, UUID, ForeignKey, Index, UniqueConstraint, Text, Integer
)
import uuid
import enum
from sqlalchemy.orm import relationship


class SenderRole(str, enum.Enum):
    """Which side of a 1-on-1 conversation sent a message."""
    CUSTOMER = "CUSTOMER"   # the shopper (users.id)
    VENDOR = "VENDOR"       # the business (Vendor.vendor_id)


class MessageKind(str, enum.Enum):
    TEXT = "TEXT"
    IMAGE = "IMAGE"             # body holds caption (optional); asset_id -> media_assets
    POST_SHARE = "POST_SHARE"   # shared_service_id -> services.id; body optional note


class Conversation(TimestampMixin, Base):
    """
    A 1-on-1 thread between a customer (user) and a vendor (business). Exactly one
    row per (customer_user_id, vendor_id) pair — enforced by a unique constraint,
    so opening a chat is an upsert-by-pair.

    Denormalized last-message fields drive the inbox list without a join/subquery
    per row; they're updated in the same transaction as each new message.
    """
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    customer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("Vendor.vendor_id"), nullable=False)

    # Inbox preview (denormalized from the latest message).
    last_message_preview = Column(String, nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    last_sender_role = Column(Enum(SenderRole), nullable=True)

    # Unread counters per side (incremented on send to the other side, zeroed on read).
    customer_unread = Column(Integer, nullable=False, default=0, server_default="0")
    vendor_unread = Column(Integer, nullable=False, default=0, server_default="0")

    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        UniqueConstraint("customer_user_id", "vendor_id", name="uq_conversation_pair"),
        # Inbox queries: "my conversations, newest activity first".
        Index("ix_conversation_customer", "customer_user_id", "last_message_at"),
        Index("ix_conversation_vendor", "vendor_id", "last_message_at"),
    )


class Message(TimestampMixin, Base):
    """
    One message in a conversation. sender_role tells us which side sent it (so the
    client renders left/right and we never have to infer identity). Content is one
    of: text (body), image (asset_id + optional body caption), or a shared post
    (shared_service_id + optional body note).
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)

    sender_role = Column(Enum(SenderRole), nullable=False)
    kind = Column(Enum(MessageKind), nullable=False, default=MessageKind.TEXT)

    body = Column(Text, nullable=True)                 # text / caption / note
    # Legacy single-image pointer. Still written (set to the FIRST attachment) for
    # backward compat; the authoritative attachment list is `attachments` below.
    asset_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=True)  # IMAGE
    shared_service_id = Column(UUID(as_uuid=True), ForeignKey("services.id"), nullable=True)  # POST_SHARE

    # Message-to-message reply threading. Points at another message in the SAME
    # conversation; the client echoes it back as `reply_to` and looks up the
    # quoted message in the already-loaded page.
    reply_to_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)

    read_at = Column(DateTime, nullable=True)          # set when the other side reads it

    conversation = relationship("Conversation", back_populates="messages")

    # Ordered attachments (0..N). Supports multiple photos and/or files per
    # message — each row points at a media_assets row (image / video / file).
    attachments = relationship(
        "MessageAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageAttachment.position",
    )

    __table_args__ = (
        # Thread pagination: messages in a conversation, newest-or-oldest first.
        Index("ix_message_conversation_created", "conversation_id", "created_at"),
    )


class MessageAttachment(TimestampMixin, Base):
    """
    One media attachment on a message, ordered by `position`. A message can carry
    several (a photo stack, a bundle of files, or a mix). Each points at a
    media_assets row, so kind/url/filename/size are resolved from there at read
    time and always reflect the asset's current (ready) state.
    """
    __tablename__ = "message_attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = Column(UUID(as_uuid=True), ForeignKey("media_assets.id"), nullable=False)
    position = Column(Integer, nullable=False, default=0, server_default="0")

    message = relationship("Message", back_populates="attachments")

    __table_args__ = (
        Index("ix_message_attachment_message", "message_id", "position"),
    )