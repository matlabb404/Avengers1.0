from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.config.db.postgresql import Base
from app.utils.mixins import TimestampMixin
import uuid


# ── Notification types ────────────────────────────────────────────────────────
# Kept as plain strings (not a DB enum) so adding a new type never needs a schema
# migration — matches the JSONB-prefs design where new types are free.
class NotificationType:
    LIKE = "LIKE"
    COMMENT = "COMMENT"
    RATING = "RATING"
    FOLLOW = "FOLLOW"
    MESSAGE = "MESSAGE"
    BOOKING = "BOOKING"              # generic / uncategorized booking event
    BOOKING_NEW = "BOOKING_NEW"            # a customer booked a vendor's service
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"  # vendor confirmed the booking
    BOOKING_CANCELLED = "BOOKING_CANCELLED"  # a booking was cancelled
    BOOKING_COMPLETED = "BOOKING_COMPLETED"  # a booking was completed
    NEW_SERVICE = "NEW_SERVICE"      # a followed vendor posted a new service
    BIG_SERVICE = "BIG_SERVICE"      # a followed vendor posted a "big" service
 
    ALL = (
        LIKE, COMMENT, RATING, FOLLOW, MESSAGE,
        BOOKING, BOOKING_NEW, BOOKING_CONFIRMED, BOOKING_CANCELLED, BOOKING_COMPLETED,
        NEW_SERVICE, BIG_SERVICE,
    )


# What the target_id points at, so the client knows where to navigate on tap.
class NotificationTarget:
    SERVICE = "SERVICE"          # a post (Service row: like, comment, rating, BIG_SERVICE)
    OFFERING = "OFFERING"        # a bookable offering (Add_Service row: NEW_SERVICE)
    VENDOR = "VENDOR"            # a vendor profile (follow)
    CONVERSATION = "CONVERSATION"  # a chat thread (message)
    BOOKING = "BOOKING"          # a booking (booking events)


class Notification(TimestampMixin, Base):
    """
    One row per notification event for a recipient. Rows are ALWAYS created (the
    in-app feed is complete); user preferences only decide whether a row also
    pushes (FCM) or is shown in the visible feed — never whether it's stored.
 
    Denormalized actor_name + preview so the feed renders without extra joins.
    """
    __tablename__ = "notifications"
 
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
 
    # Who receives this notification.
    recipient_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
 
    # One of NotificationType.* (string, not enum — new types need no migration).
    type = Column(String, nullable=False)
 
    # Who triggered it (nullable for system-generated events).
    actor_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
 
    # What it's about: target_type is one of NotificationTarget.*, target_id is the
    # uuid/string id of that entity (kept as String to tolerate non-uuid ids).
    target_type = Column(String, nullable=True)
    target_id = Column(String, nullable=True)
 
    # Denormalized display fields (so the list renders without N+1 lookups).
    actor_name = Column(String, nullable=True)     # e.g. "Bahdja Catering"
    preview = Column(String, nullable=True)        # e.g. comment text / message snippet
 
    # Read state. NULL = unread; set to a timestamp when read.
    read_at = Column(DateTime(timezone=True), nullable=True)
 
    # Whether this row is visible in the feed. Always stored; if False the row is
    # "saved but hidden" per the user's per-type 'show' preference at creation time.
    show_in_feed = Column(Boolean, nullable=False, server_default=text("true"))
 
    recipient = relationship(
        "User",
        foreign_keys=[recipient_user_id],
    )
    actor = relationship(
        "User",
        foreign_keys=[actor_user_id],
    )
 
    __table_args__ = (
        # Fast "my unread, newest first" and "my feed, newest first" queries.
        Index(
            "ix_notifications_recipient_created",
            "recipient_user_id", "created_at",
        ),
        Index(
            "ix_notifications_recipient_unread",
            "recipient_user_id", "read_at",
        ),
    )
    

class NotificationPreference(Base):
    """
    Per-user notification settings. One row per user. `prefs` is a JSONB map of
        type -> {"push": bool, "show": bool}
    Missing keys default to {"push": true, "show": true} in code (see
    notification_module.effective_pref), so new types are automatically on without
    a migration or backfill.

    Example prefs value:
        {
          "LIKE":    {"push": true,  "show": true},
          "COMMENT": {"push": true,  "show": true},
          "FOLLOW":  {"push": false, "show": true},   # saved + shown, but no push
          "MESSAGE": {"push": true,  "show": true},
          "BOOKING": {"push": true,  "show": true}
        }
    """
    __tablename__ = "notification_preferences"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # JSONB so we can index/query if ever needed; defaults to an empty object.
    prefs = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    user = relationship("User", foreign_keys=[user_id])

class VendorNotificationMute(TimestampMixin, Base):
    """
    A user muting a specific vendor's notifications, per TYPE. Presence of a row
    == muted for that (user, vendor, type). Absence == not muted (fall back to the
    user's global per-type preference).

    Muted notifications are still STORED but hidden (show_in_feed=False) and not
    pushed — consistent with the 'saved vs shown' model. Per-type so a user can
    mute a vendor's BIG_SERVICE (posts) while still getting NEW_SERVICE (offerings)
    or a future BOOKING_REMINDER.
    """
    __tablename__ = "vendor_notification_mutes"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        primary_key=True,
    )
    type = Column(String, primary_key=True)   # one of NotificationType.*