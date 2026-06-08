"""
Following routes.

prefix = /following

    POST   /following/{vendor_id}          -> follow a vendor (idempotent)
    DELETE /following/{vendor_id}          -> unfollow (idempotent)
    GET    /following/status/{vendor_id}   -> {is_following, follower_count}
    GET    /following/feed                 -> paginated feed of followed vendors' posts

The feed is PERSONALIZED, so it is explicitly marked `private, no-store` — the
CDN must never cache one user's feed and serve it to another. (Discover, which
is global-by-region, is the one that gets edge-cached; it lives separately.)

ROUTE ORDERING: /status/{vendor_id} and /feed are literal-prefixed, so they
don't collide with /{vendor_id}. Still, /feed is declared before the bare
parameterized routes out of habit/safety.

Place at: app/routers/following_router.py
Register in main.py:  app.include_router(following_router.router)
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import social_module
from app.modules.account_module import get_current_user
from app.schemas.social_schema import (
    FollowResponse,
    FollowStatusResponse,
    FeedPage,
)

router = APIRouter(prefix="/following", tags=["following"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Feed (personalized — never cached) ───────────────────────────────────────

@router.get("/feed", response_model=FeedPage)
def following_feed(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Posts from vendors the current user follows, newest first.
    Empty list (with an empty-state UI) when the user follows nobody.
    """
    # Personalized response: forbid any shared/edge caching.
    response.headers["Cache-Control"] = "private, no-store"
    return social_module.get_following_feed(
        db, current_user, limit=limit, cursor=cursor
    )


# ── Follow status (for the vendor profile view) ──────────────────────────────

@router.get("/status/{vendor_id}", response_model=FollowStatusResponse)
def follow_status(
    vendor_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Whether the current actor follows this vendor, plus the vendor's follower count."""
    response.headers["Cache-Control"] = "private, no-store"  # is_following is per-user
    return FollowStatusResponse(
        vendor_id=vendor_id,
        is_following=social_module.is_following(db, current_user, vendor_id),
        follower_count=social_module.follower_count(db, vendor_id),
    )


# ── Follow / Unfollow ────────────────────────────────────────────────────────

@router.post("/{vendor_id}", response_model=FollowResponse)
def follow(
    vendor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_module.follow_vendor(db, current_user, vendor_id)


@router.delete("/{vendor_id}", response_model=FollowResponse)
def unfollow(
    vendor_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_module.unfollow_vendor(db, current_user, vendor_id)