"""
Cursor pagination is keyset-based on (created_at, id): the cursor encodes the
last item's created_at + id, and the next page asks for rows strictly "older"
than that. 
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.big_services_schema import FullServiceResponse


# ── Follow / unfollow responses ──────────────────────────────────────────────

class FollowResponse(BaseModel):
    following: bool
    already: bool = False      # follow: was it already followed?
    removed: bool = False      # unfollow: was a row actually removed?


class FollowStatusResponse(BaseModel):
    """For the vendor profile view: am I following, and how many followers."""
    vendor_id: UUID
    is_following: bool
    follower_count: int


# ── Engagement counts (denormalized, global, cache-safe) ─────────────────────

class EngagementCounts(BaseModel):
    like_count: int = 0
    comment_count: int = 0
    rating_count: int = 0
    rating_avg: Optional[float] = None    # rating_sum / rating_count, or null


# ── Feed item: a post plus its global counts ─────────────────────────────────

class FeedItem(BaseModel):
    post: FullServiceResponse
    counts: EngagementCounts


# ── Paginated feed envelope ──────────────────────────────────────────────────

class FeedPage(BaseModel):
    """
    A page of feed items plus an opaque cursor for the next page.

    next_cursor is null when there are no more items. Pass it back as
    ?cursor=<next_cursor> to fetch the following page.
    """
    items: list[FeedItem] = Field(default_factory=list)
    next_cursor: Optional[str] = None


# ── Like responses ───────────────────────────────────────────────────────────

class LikeResponse(BaseModel):
    liked: bool
    like_count: int
    already: bool = False      # like: was it already liked?
    removed: bool = False      # unlike: was a row actually removed?


class LikedFlagsRequest(BaseModel):
    """Ask which of these posts the current user has liked (batch, 1 query)."""
    service_ids: list[UUID] = Field(default_factory=list)


class LikedFlagsResponse(BaseModel):
    """The subset of the requested ids that the current user has liked."""
    liked_ids: list[UUID] = Field(default_factory=list)


# ── Comment / rating DTOs ────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    """
    Create a comment and/or rating. Provide body, stars, or both.
    - parent_id set -> a reply (one level deep, no rating allowed).
    - stars set -> a rating; booking_id REQUIRED and must be a completed booking
      owned by the caller for this post.
    """
    body: Optional[str] = Field(None, max_length=2000)
    stars: Optional[int] = Field(None, ge=1, le=5)
    parent_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None


class CommentEdit(BaseModel):
    """Edit text and/or rating value on one's own comment. Send what changes."""
    body: Optional[str] = Field(None, max_length=2000)
    stars: Optional[int] = Field(None, ge=1, le=5)


class CommentAuthor(BaseModel):
    """Who wrote it — resolved to whichever of customer/vendor authored the row."""
    kind: str                       # "customer" | "vendor"
    id: UUID


class CommentOut(BaseModel):
    id: UUID
    service_id: UUID
    author: CommentAuthor
    body: Optional[str] = None
    stars: Optional[int] = None
    parent_id: Optional[UUID] = None
    booking_id: Optional[UUID] = None
    created_at: datetime
    edited_at: Optional[datetime] = None
    reply_count: int = 0            # number of replies (top-level rows only)


class CommentPage(BaseModel):
    items: list[CommentOut] = Field(default_factory=list)
    next_cursor: Optional[str] = None


class DeleteResponse(BaseModel):
    deleted: bool