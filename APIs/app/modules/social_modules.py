"""
ACTOR RESOLUTION is the keystone of every social action /customer or vendor.#
resolve_actor() turns a User into exactly one of those, so handlers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account_model import User
from app.models.customer_model import customer
from app.models.vendor_model import Vendor
from app.models.social_model import Following


ActorKind = Literal["customer", "vendor"]


@dataclass
class Actor:
    """The resolved acting identity behind a request."""
    kind: ActorKind
    id: UUID                # customer_id or vendor_id
    user_id: UUID

    @property
    def is_vendor(self) -> bool:
        return self.kind == "vendor"

    @property
    def is_customer(self) -> bool:
        return self.kind == "customer"


# ── Actor resolution ──────────────────────────────────────────────────────────

def resolve_actor(
    db: Session, user: User, prefer: Optional[ActorKind] = None
) -> Actor:
    """
    Resolve a User into their acting role (customer or vendor).

    prefer:
        None     -> if the user has both profiles, vendor wins.
        "vendor" -> use the vendor profile (404 if none).
        "customer" -> use the customer profile (404 if none).
    """
    vendor_row = (
        db.query(Vendor).filter(Vendor.user_id == user.id).first()
        if prefer in (None, "vendor")
        else None
    )
    customer_row = (
        db.query(customer).filter(customer.user_id == user.id).first()
        if prefer in (None, "customer")
        else None
    )

    if prefer == "vendor":
        vendor_row = db.query(Vendor).filter(Vendor.user_id == user.id).first()
        if not vendor_row:
            raise HTTPException(403, "No vendor profile for this account")
        return Actor("vendor", vendor_row.vendor_id, user.id)

    if prefer == "customer":
        customer_row = db.query(customer).filter(customer.user_id == user.id).first()
        if not customer_row:
            raise HTTPException(403, "No customer profile for this account")
        return Actor("customer", customer_row.customer_id, user.id)

    # No preference: vendor takes precedence if present.
    if vendor_row:
        return Actor("vendor", vendor_row.vendor_id, user.id)
    if customer_row:
        return Actor("customer", customer_row.customer_id, user.id)

    raise HTTPException(
        403, "Account has no customer or vendor profile; complete your profile first"
    )


def _follower_filter(actor: Actor):
    """SQLAlchemy filter selecting `following` rows authored by this actor."""
    if actor.is_customer:
        return and_(
            Following.follower_customer_id == actor.id,
            Following.follower_vendor_id.is_(None),
        )
    return and_(
        Following.follower_vendor_id == actor.id,
        Following.follower_customer_id.is_(None),
    )


# ── Follow / Unfollow ───────────────────────────────────────────────────────────

def follow_vendor(db: Session, user: User, vendor_id: UUID) -> dict:
    """
    Follow a vendor. Idempotent: following an already-followed vendor is a no-op.
    Blocks self-follow (a vendor can't follow itself). Vendor-follows-vendor is
    allowed and surfaced.
    """
    actor = resolve_actor(db, user)

    # Target must exist.
    target = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not target:
        raise HTTPException(404, "Vendor not found")

    # Block self-follow.
    if actor.is_vendor and actor.id == vendor_id:
        raise HTTPException(400, "You cannot follow yourself")

    row = Following(
        vendor_id=vendor_id,
        follower_customer_id=actor.id if actor.is_customer else None,
        follower_vendor_id=actor.id if actor.is_vendor else None,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # uq_following violated -> already following. Idempotent success.
        db.rollback()
        return {"following": True, "already": True}

    return {"following": True, "already": False}


def unfollow_vendor(db: Session, user: User, vendor_id: UUID) -> dict:
    """Unfollow a vendor. Idempotent: unfollowing when not following is a no-op."""
    actor = resolve_actor(db, user)

    deleted = (
        db.query(Following)
        .filter(Following.vendor_id == vendor_id, _follower_filter(actor))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"following": False, "removed": bool(deleted)}


def is_following(db: Session, user: User, vendor_id: UUID) -> bool:
    """Does the current actor follow this vendor? Used for vendor profile views."""
    actor = resolve_actor(db, user)
    row = (
        db.query(Following.id)
        .filter(Following.vendor_id == vendor_id, _follower_filter(actor))
        .first()
    )
    return row is not None


def follower_count(db: Session, vendor_id: UUID) -> int:
    """How many accounts follow this vendor (customers + vendors)."""
    return (
        db.query(Following.id)
        .filter(Following.vendor_id == vendor_id)
        .count()
    )


# ── Following feed ──────────────────────────────────────────────────────────────

def get_followed_vendor_ids(db: Session, actor: Actor) -> list[UUID]:
    """The vendor_ids this actor follows."""
    rows = (
        db.query(Following.vendor_id)
        .filter(_follower_filter(actor))
        .all()
    )
    return [r[0] for r in rows]


# ── Cursor codec (keyset pagination on (created_at, id)) ─────────────────────

import base64
from datetime import datetime, timezone


def _encode_cursor(created_at: datetime, sid: UUID) -> str:
    """Opaque cursor: base64 of '<iso8601>|<uuid>'. Survives URL round-trips."""
    raw = f"{created_at.isoformat()}|{sid}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        ts_str, id_str = raw.split("|", 1)
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts, UUID(id_str)
    except Exception:
        raise HTTPException(400, "Invalid cursor")


# ── Counts helper ────────────────────────────────────────────────────────────

def _counts_for(service) -> dict:
    """Read the denormalized counters off a Service row into the schema shape."""
    rating_count = service.rating_count or 0
    rating_sum = service.rating_sum or 0
    rating_avg = (rating_sum / rating_count) if rating_count > 0 else None
    return {
        "like_count": service.like_count or 0,
        "comment_count": service.comment_count or 0,
        "rating_count": rating_count,
        "rating_avg": round(rating_avg, 2) if rating_avg is not None else None,
    }


# ── Following feed ───────────────────────────────────────────────────────────

# Imported lazily inside the function to avoid a circular import at module load
# (big_services_module imports schemas that import nothing social, but keep the
# direction clean: social -> big_services, never the reverse).

def get_following_feed(
    db: Session, user: User, limit: int = 20, cursor: Optional[str] = None
) -> dict:
    """
    Posts from vendors the current actor follows, newest first, keyset-paginated.

    Returns a dict matching FeedPage: {items: [{post, counts}], next_cursor}.
    Empty when the actor follows nobody (UI shows an empty state).
    Personalized -> the router marks this response private/no-store.
    """
    from app.models.service_model import Service, Add_Service, price_history
    from app.models.vendor_model import Vendor
    from app.modules.big_services_module import _build_full_response

    actor = resolve_actor(db, user)
    followed = get_followed_vendor_ids(db, actor)
    if not followed:
        return {"items": [], "next_cursor": None}

    limit = max(1, min(limit, 50))  # clamp page size

    q = (
        db.query(Service, Vendor, price_history, Add_Service)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .join(price_history, Service.price_history == price_history.id)
        .filter(Service.add_vendor_id.in_(followed))
    )

    # Keyset: rows strictly older than the cursor, by (created_at DESC, id DESC).
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Service.created_at < c_ts,
                and_(Service.created_at == c_ts, Service.id < c_id),
            )
        )

    q = q.order_by(Service.created_at.desc(), Service.id.desc()).limit(limit + 1)
    rows = q.all()

    # We fetched limit+1 to know whether a next page exists.
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for service, vendor, ph, add_service in rows:
        post = _build_full_response(db, service, vendor, ph, add_service)
        items.append({"post": post, "counts": _counts_for(service)})

    next_cursor = None
    if has_more and rows:
        last_service = rows[-1][0]
        next_cursor = _encode_cursor(last_service.created_at, last_service.id)

    return {"items": items, "next_cursor": next_cursor}


# ═════════════════════════════════════════════════════════════════════════════
# LIKES
# ═════════════════════════════════════════════════════════════════════════════
#
# Counter discipline: like_count on the Service row is maintained in the SAME
# transaction as the like insert/delete, so the denormalized count can never
# drift from the actual row count. The UNIQUE constraint (uq_like) makes a
# double-like a no-op (caught as IntegrityError -> we DON'T increment again).

from app.models.social_model import Like


def _liker_filter(actor: Actor):
    """SQLAlchemy filter selecting `likes` rows authored by this actor."""
    if actor.is_customer:
        return and_(
            Like.liker_customer_id == actor.id,
            Like.liker_vendor_id.is_(None),
        )
    return and_(
        Like.liker_vendor_id == actor.id,
        Like.liker_customer_id.is_(None),
    )


def like_post(db: Session, user: User, service_id: UUID) -> dict:
    """
    Like a post. Idempotent: a second like by the same actor is a no-op and does
    NOT double-increment the counter. like_count is bumped in the same commit.
    """
    from app.models.service_model import Service

    actor = resolve_actor(db, user)

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Post not found")

    row = Like(
        service_id=service_id,
        liker_customer_id=actor.id if actor.is_customer else None,
        liker_vendor_id=actor.id if actor.is_vendor else None,
    )
    db.add(row)
    try:
        # Flush first so a duplicate trips the UNIQUE constraint BEFORE we touch
        # the counter — that way an already-liked post doesn't inflate the count.
        db.flush()
    except IntegrityError:
        db.rollback()
        return {"liked": True, "already": True, "like_count": service.like_count or 0}

    service.like_count = (service.like_count or 0) + 1
    db.commit()
    return {"liked": True, "already": False, "like_count": service.like_count}


def unlike_post(db: Session, user: User, service_id: UUID) -> dict:
    """
    Unlike a post. Idempotent: if no like existed, the counter is untouched.
    Decrement happens in the same commit as the delete, floored at 0.
    """
    from app.models.service_model import Service

    actor = resolve_actor(db, user)

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Post not found")

    deleted = (
        db.query(Like)
        .filter(Like.service_id == service_id, _liker_filter(actor))
        .delete(synchronize_session=False)
    )

    if deleted:
        service.like_count = max((service.like_count or 0) - deleted, 0)

    db.commit()
    return {
        "liked": False,
        "removed": bool(deleted),
        "like_count": service.like_count or 0,
    }


def is_liked(db: Session, user: User, service_id: UUID) -> bool:
    """Has the current actor liked this post? Per-user — never edge-cached."""
    actor = resolve_actor(db, user)
    row = (
        db.query(Like.id)
        .filter(Like.service_id == service_id, _liker_filter(actor))
        .first()
    )
    return row is not None


def liked_service_ids(db: Session, user: User, service_ids: list[UUID]) -> set[UUID]:
    """
    Which of these posts has the current actor liked? Batch lookup so a feed/
    Discover page can fetch all per-user like flags in ONE query (the client
    merges these into the cached, count-only post data).
    """
    if not service_ids:
        return set()
    actor = resolve_actor(db, user)
    rows = (
        db.query(Like.service_id)
        .filter(Like.service_id.in_(service_ids), _liker_filter(actor))
        .all()
    )
    return {r[0] for r in rows}


# ═════════════════════════════════════════════════════════════════════════════
# DISCOVER  (global, ranked BY REGION — edge-cacheable)
# ═════════════════════════════════════════════════════════════════════════════
#
# Unlike the Following feed, Discover is the SAME for everyone in a given region,
# so the router marks it `public, max-age=120` and Cloudflare caches one copy per
# region. That means:
#   - region arrives as a URL query param (a STRING the client already resolved
#     from GPS->reverse-geocode, falling back to profile city). NEVER raw lat/lng
#     (every device would be a unique URL -> zero cache hits).
#   - NO auth requirement and NO per-user fields in the body (is_liked /
#     is_following are fetched separately via the per-user batch endpoints), or
#     the response couldn't be shared.
#   - counts ride along from the denormalized Service columns — including
#     rating_avg, which is the "ratings cached, refreshed every 2 min" behavior
#     (the 2 min IS the max-age).
#
# v1 ranking = recency within region (created_at DESC, id DESC). v2 can swap the
# ORDER BY for a popularity score without changing the URL or response shape —
# isolated in _discover_order_by() below.


def _discover_order_by():
    """
    v1: pure recency. To upgrade to popularity later, return a scored expression
    here (e.g. weighting like_count / rating_avg / recency) — nothing else in the
    endpoint or response shape needs to change.
    """
    from app.models.service_model import Service
    return (Service.created_at.desc(), Service.id.desc())


def get_discover_feed(
    db: Session,
    region: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> dict:
    """
    Global, region-filtered post feed. No auth, no per-user fields — safe to
    edge-cache per region. Returns FeedPage shape: {items:[{post,counts}], next_cursor}.

    region:
        a resolved region string matched against Vendor.city (case-insensitive).
        None / "everywhere" -> no region filter (the global firehose), also cacheable.
    """
    from app.models.service_model import Service, Add_Service, price_history
    from app.models.vendor_model import Vendor
    from app.modules.big_services_module import _build_full_response

    limit = max(1, min(limit, 50))

    q = (
        db.query(Service, Vendor, price_history, Add_Service)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .join(price_history, Service.price_history == price_history.id)
    )

    # Region filter (skip for None / "everywhere"). Case-insensitive match on city.
    if region and region.strip().lower() not in ("", "everywhere"):
        q = q.filter(func.lower(Vendor.city) == region.strip().lower())

    # Keyset pagination, same (created_at, id) scheme as the Following feed.
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Service.created_at < c_ts,
                and_(Service.created_at == c_ts, Service.id < c_id),
            )
        )

    q = q.order_by(*_discover_order_by()).limit(limit + 1)
    rows = q.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for service, vendor, ph, add_service in rows:
        post = _build_full_response(db, service, vendor, ph, add_service)
        items.append({"post": post, "counts": _counts_for(service)})

    next_cursor = None
    if has_more and rows:
        last_service = rows[-1][0]
        next_cursor = _encode_cursor(last_service.created_at, last_service.id)

    return {"items": items, "next_cursor": next_cursor}


# ═════════════════════════════════════════════════════════════════════════════
# COMMENTS  (+ optional rating, merged into the same row/table)
# ═════════════════════════════════════════════════════════════════════════════
#
# A comment row may carry: body (text), stars (rating), or both. Rules:
#   - exactly one author (customer xor vendor) — enforced by CHECK + resolve_actor
#   - has_content: body OR stars (CHECK)
#   - a rating (stars) REQUIRES a completed booking owned by the actor for THIS
#     service, and is TOP-LEVEL only (parent_id NULL)
#   - one rating per booking (uq_comment_rating_per_booking)
#   - replies are one level deep: a reply (parent_id set) cannot be replied to,
#     and cannot carry a rating
#
# Counter discipline (all in the same commit as the row write):
#   comment_count += 1   when a row HAS body
#   rating_count  += 1   and rating_sum += stars   when a row HAS stars
# A row with both bumps both. Edits/deletes reverse precisely what they changed.

from app.models.social_model import Comment


def _resolve_author_columns(actor: Actor) -> dict:
    return {
        "author_customer_id": actor.id if actor.is_customer else None,
        "author_vendor_id": actor.id if actor.is_vendor else None,
    }


def _author_filter(actor: Actor):
    """Filter selecting comment rows authored by this actor (for edit/delete ownership)."""
    if actor.is_customer:
        return and_(
            Comment.author_customer_id == actor.id,
            Comment.author_vendor_id.is_(None),
        )
    return and_(
        Comment.author_vendor_id == actor.id,
        Comment.author_customer_id.is_(None),
    )


def _validate_rating_booking(db: Session, actor: Actor, service_id: UUID, booking_id: UUID):
    """
    A rating is only valid if the booking is COMPLETED, owned by the actor's
    user, and for this service. Raises HTTPException otherwise.
    """
    from app.models.booking_model import Booking, BookingStatus

    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.user_id != actor.user_id:
        raise HTTPException(403, "You can only rate your own bookings")
    if booking.service_id != service_id:
        raise HTTPException(400, "Booking does not match this post")
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(409, "You can only rate a completed booking")


def add_comment(
    db: Session,
    user: User,
    service_id: UUID,
    body: Optional[str] = None,
    stars: Optional[int] = None,
    parent_id: Optional[UUID] = None,
    booking_id: Optional[UUID] = None,
) -> Comment:
    """
    Create a comment and/or rating on a post. Maintains the denormalized counters
    atomically. See module header for the full rule set.
    """
    from app.models.service_model import Service

    actor = resolve_actor(db, user)

    # Content presence (mirrors the DB CHECK, but gives a clean 400).
    has_body = body is not None and body.strip() != ""
    has_rating = stars is not None
    if not has_body and not has_rating:
        raise HTTPException(400, "A comment must have text, a rating, or both")

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Post not found")

    # Threading rules.
    if parent_id is not None:
        parent = db.query(Comment).filter(Comment.id == parent_id).first()
        if not parent:
            raise HTTPException(404, "Parent comment not found")
        if parent.service_id != service_id:
            raise HTTPException(400, "Parent comment belongs to a different post")
        if parent.parent_id is not None:
            raise HTTPException(400, "Replies can only be one level deep")
        if has_rating:
            raise HTTPException(400, "A rating must be a top-level comment")

    # Rating rules.
    if has_rating:
        if not (1 <= stars <= 5):
            raise HTTPException(400, "Stars must be between 1 and 5")
        if booking_id is None:
            raise HTTPException(400, "A rating requires the booking it is based on")
        _validate_rating_booking(db, actor, service_id, booking_id)
    else:
        # No stars -> ignore any stray booking_id (a plain comment isn't tied to one).
        booking_id = None

    row = Comment(
        service_id=service_id,
        body=body if has_body else None,
        stars=stars if has_rating else None,
        booking_id=booking_id,
        parent_id=parent_id,
        **_resolve_author_columns(actor),
    )
    db.add(row)
    try:
        db.flush()  # surface uq_comment_rating_per_booking (one rating/booking) as 409
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You have already rated this booking")

    # Counters — same commit.
    if has_body:
        service.comment_count = (service.comment_count or 0) + 1
    if has_rating:
        service.rating_count = (service.rating_count or 0) + 1
        service.rating_sum = (service.rating_sum or 0) + stars

    db.commit()
    db.refresh(row)
    return row


def edit_comment(
    db: Session,
    user: User,
    comment_id: UUID,
    body: Optional[str] = None,
    stars: Optional[int] = None,
) -> Comment:
    """
    Edit one's own comment text and/or rating value. Adjusts counters by the
    DELTA only (e.g. changing stars 4->5 adds 1 to rating_sum; adding text to a
    rating-only row bumps comment_count). Author-only.
    """
    from app.models.service_model import Service

    actor = resolve_actor(db, user)
    row = (
        db.query(Comment)
        .filter(Comment.id == comment_id, _author_filter(actor))
        .first()
    )
    if not row:
        raise HTTPException(404, "Comment not found")

    service = db.query(Service).filter(Service.id == row.service_id).first()

    # ---- body delta ----
    if body is not None:
        new_has_body = body.strip() != ""
        old_has_body = row.body is not None and row.body.strip() != ""
        if new_has_body and not old_has_body:
            service.comment_count = (service.comment_count or 0) + 1
        elif not new_has_body and old_has_body:
            service.comment_count = max((service.comment_count or 0) - 1, 0)
        row.body = body if new_has_body else None

    # ---- stars delta ----
    if stars is not None:
        # Editing a rating only makes sense on a row that already IS a rating
        # (you can't retro-add a rating without going through the booking check).
        if row.stars is None:
            raise HTTPException(
                400,
                "This comment isn't a rating; create a rating via the booking instead",
            )
        if not (1 <= stars <= 5):
            raise HTTPException(400, "Stars must be between 1 and 5")
        old_stars = row.stars or 0
        service.rating_sum = (service.rating_sum or 0) + (stars - old_stars)
        row.stars = stars

    # Guard: don't let an edit empty the row entirely.
    if (row.body is None) and (row.stars is None):
        db.rollback()
        raise HTTPException(400, "A comment must keep text, a rating, or both")

    from datetime import datetime, timezone
    row.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def delete_comment(db: Session, user: User, comment_id: UUID) -> dict:
    """
    Delete one's own comment. Reverses exactly the counters this row contributed.
    Deleting a top-level comment cascades to its replies (FK ondelete CASCADE +
    relationship cascade); each cascaded reply's body also needs to be removed
    from comment_count, so we account for replies explicitly here.
    Author-only.
    """
    from app.models.service_model import Service

    actor = resolve_actor(db, user)
    row = (
        db.query(Comment)
        .filter(Comment.id == comment_id, _author_filter(actor))
        .first()
    )
    if not row:
        raise HTTPException(404, "Comment not found")

    service = db.query(Service).filter(Service.id == row.service_id).first()

    # Account for this row's own contributions.
    body_removed = 1 if (row.body is not None and row.body.strip() != "") else 0
    rating_removed = 1 if row.stars is not None else 0
    rating_sum_removed = row.stars or 0

    # Account for replies that will be cascade-deleted (replies never carry
    # ratings, so only body counts matter).
    if row.parent_id is None:
        replies = db.query(Comment).filter(Comment.parent_id == row.id).all()
        for r in replies:
            if r.body is not None and r.body.strip() != "":
                body_removed += 1

    if service:
        service.comment_count = max((service.comment_count or 0) - body_removed, 0)
        service.rating_count = max((service.rating_count or 0) - rating_removed, 0)
        service.rating_sum = max((service.rating_sum or 0) - rating_sum_removed, 0)

    db.delete(row)  # cascade removes replies
    db.commit()
    return {"deleted": True}


# ── Reads ────────────────────────────────────────────────────────────────────

def list_comments(
    db: Session, service_id: UUID, limit: int = 20, cursor: Optional[str] = None
) -> dict:
    """
    Top-level comments for a post, newest first, keyset-paginated. Replies are
    NOT inlined here — fetch them per-parent via list_replies (keeps payloads
    bounded). Returns {items:[Comment...], next_cursor}.
    """
    q = db.query(Comment).filter(
        Comment.service_id == service_id,
        Comment.parent_id.is_(None),
    )
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Comment.created_at < c_ts,
                and_(Comment.created_at == c_ts, Comment.id < c_id),
            )
        )
    limit = max(1, min(limit, 50))
    rows = q.order_by(Comment.created_at.desc(), Comment.id.desc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        _encode_cursor(rows[-1].created_at, rows[-1].id) if (has_more and rows) else None
    )
    return {"items": rows, "next_cursor": next_cursor}


def list_replies(
    db: Session, parent_id: UUID, limit: int = 20, cursor: Optional[str] = None
) -> dict:
    """Replies under a top-level comment, OLDEST first (natural reading order)."""
    q = db.query(Comment).filter(Comment.parent_id == parent_id)
    if cursor:
        c_ts, c_id = _decode_cursor(cursor)
        q = q.filter(
            or_(
                Comment.created_at > c_ts,
                and_(Comment.created_at == c_ts, Comment.id > c_id),
            )
        )
    limit = max(1, min(limit, 50))
    rows = q.order_by(Comment.created_at.asc(), Comment.id.asc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        _encode_cursor(rows[-1].created_at, rows[-1].id) if (has_more and rows) else None
    )
    return {"items": rows, "next_cursor": next_cursor}


# ── Comment -> DTO dict (author resolved, reply_count for top-level) ─────────

def comment_to_out(db: Session, c: Comment, include_reply_count: bool = True) -> dict:
    """
    Shape a Comment row into the CommentOut schema: collapse the two author FKs
    into {kind, id}, and (for top-level rows) count replies. Pass
    include_reply_count=False when rendering replies themselves (always 0).
    """
    if c.author_customer_id is not None:
        author = {"kind": "customer", "id": c.author_customer_id}
    else:
        author = {"kind": "vendor", "id": c.author_vendor_id}

    reply_count = 0
    if include_reply_count and c.parent_id is None:
        reply_count = (
            db.query(Comment.id).filter(Comment.parent_id == c.id).count()
        )

    return {
        "id": c.id,
        "service_id": c.service_id,
        "author": author,
        "body": c.body,
        "stars": c.stars,
        "parent_id": c.parent_id,
        "booking_id": c.booking_id,
        "created_at": c.created_at,
        "edited_at": c.edited_at,
        "reply_count": reply_count,
    }