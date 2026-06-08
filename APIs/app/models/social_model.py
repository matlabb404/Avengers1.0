"""
Identity model: a follower / commenter / liker / rater can be EITHER a customer
or a vendor.

Ratings are merged INTO comments: a comment row may optionally carry `stars`
(1–5). A rating is only valid when backed by a COMPLETED booking, enforced both
by a CHECK (stars requires booking_id) and by the handler (which verifies the
booking is completed, belongs to the actor, and is for this service).

Denormalized counters live on Service (services table) — see service_model.py:
    like_count, comment_count, rating_count, rating_sum
maintained atomically by the handlers.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, SmallInteger, DateTime, UUID, ForeignKey,
    CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.utils.mixins import TimestampMixin
from app.config.db.postgresql import Base


# ─────────────────────────────────────────────────────────────
# Following — a (customer|vendor) follows a Vendor
# ─────────────────────────────────────────────────────────────

class Following(TimestampMixin, Base):
    __tablename__ = "following"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Who is followed — always a vendor (customers can't be followed).
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        nullable=False,
    )

    # The follower — exactly one of these is set.
    follower_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer.customer_id", ondelete="CASCADE"),
        nullable=True,
    )
    follower_vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        nullable=True,
    )

    # The vendor being followed. foreign_keys disambiguates from follower_vendor_id.
    followed_vendor = relationship(
        "Vendor", foreign_keys=[vendor_id], back_populates="followers"
    )
    follower_customer = relationship(
        "customer", foreign_keys=[follower_customer_id], back_populates="following"
    )
    follower_vendor = relationship(
        "Vendor", foreign_keys=[follower_vendor_id], back_populates="following"
    )

    __table_args__ = (
        CheckConstraint(
            "(follower_customer_id IS NOT NULL)::int + "
            "(follower_vendor_id IS NOT NULL)::int = 1",
            name="ck_following_one_follower",
        ),
        UniqueConstraint(
            "vendor_id", "follower_customer_id", "follower_vendor_id",
            name="uq_following",
        ),
        Index("ix_following_vendor", "vendor_id"),
        Index("ix_following_follower_customer", "follower_customer_id"),
        Index("ix_following_follower_vendor", "follower_vendor_id"),
    )


# ─────────────────────────────────────────────────────────────
# Comments (+ optional rating)
# ─────────────────────────────────────────────────────────────

class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Author — exactly one of these is set.
    author_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer.customer_id", ondelete="CASCADE"),
        nullable=True,
    )
    author_vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        nullable=True,
    )

    body = Column(Text, nullable=True)  # nullable: a pure rating may have no text

    # One level of threading. A reply has parent_id set; a reply cannot itself
    # be replied to (enforced in the handler, not the schema).
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Optional rating, earned by a COMPLETED booking. Ratings are top-level only
    # (parent_id NULL) — enforced in the handler.
    stars = Column(SmallInteger, nullable=True)
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("booking.booking_id", ondelete="CASCADE"),
        nullable=True,
    )
    edited_at = Column(DateTime, nullable=True)

    # Relationships
    service = relationship("Service", back_populates="comments")
    author_customer = relationship(
        "customer", foreign_keys=[author_customer_id], back_populates="comments"
    )
    author_vendor = relationship(
        "Vendor", foreign_keys=[author_vendor_id], back_populates="comments"
    )
    booking = relationship("Booking", back_populates="rating")
    # Self-referential threading
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship(
        "Comment", back_populates="parent", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "(author_customer_id IS NOT NULL)::int + "
            "(author_vendor_id IS NOT NULL)::int = 1",
            name="ck_comment_one_author",
        ),
        # A row must say something: text or a rating (or both).
        CheckConstraint(
            "body IS NOT NULL OR stars IS NOT NULL",
            name="ck_comment_has_content",
        ),
        # Stars valid range.
        CheckConstraint(
            "stars IS NULL OR (stars BETWEEN 1 AND 5)",
            name="ck_comment_stars_range",
        ),
        # A rating must be backed by a booking.
        CheckConstraint(
            "stars IS NULL OR booking_id IS NOT NULL",
            name="ck_comment_rating_needs_booking",
        ),
        # One rating per booking (NULL booking_ids don't collide, so plain
        # comments are unlimited).
        UniqueConstraint("booking_id", name="uq_comment_rating_per_booking"),
        Index("ix_comments_service_created", "service_id", "created_at"),
        Index("ix_comments_parent", "parent_id"),
        Index("ix_comments_author_customer", "author_customer_id"),
        Index("ix_comments_author_vendor", "author_vendor_id"),
    )


# ─────────────────────────────────────────────────────────────
# Likes — a (customer|vendor) likes a Service (post)
# ─────────────────────────────────────────────────────────────

class Like(TimestampMixin, Base):
    __tablename__ = "likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
    )

    liker_customer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("customer.customer_id", ondelete="CASCADE"),
        nullable=True,
    )
    liker_vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        nullable=True,
    )

    service = relationship("Service", back_populates="likes")
    liker_customer = relationship(
        "customer", foreign_keys=[liker_customer_id], back_populates="likes"
    )
    liker_vendor = relationship(
        "Vendor", foreign_keys=[liker_vendor_id], back_populates="likes"
    )

    __table_args__ = (
        CheckConstraint(
            "(liker_customer_id IS NOT NULL)::int + "
            "(liker_vendor_id IS NOT NULL)::int = 1",
            name="ck_like_one_liker",
        ),
        UniqueConstraint(
            "service_id", "liker_customer_id", "liker_vendor_id",
            name="uq_like",
        ),
        Index("ix_likes_service", "service_id"),
        Index("ix_likes_liker_customer", "liker_customer_id"),
        Index("ix_likes_liker_vendor", "liker_vendor_id"),
    )