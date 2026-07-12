from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import social_module
from app.modules.account_module import get_current_user
from app.schemas.social_schema import BookmarkResponse, FeedPage

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BookmarkStatusResponse(BaseModel):
    service_id: UUID
    is_bookmarked: bool


# ── Saved list (the "Saved" tab) ─────────────────────────────────────────────

@router.get("", response_model=FeedPage)
def list_bookmarks(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The current actor's saved posts, most-recently-SAVED first (not most-recently
    posted). Same FeedPage shape as every other feed, so the client reuses the grid.
    """
    response.headers["Cache-Control"] = "private, no-store"
    return social_module.get_bookmarked_feed(db, current_user, limit=limit, cursor=cursor)


# ── Single-post status (literal path before /{service_id}) ───────────────────

@router.get("/status/{service_id}", response_model=BookmarkStatusResponse)
def bookmark_status(
    service_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return BookmarkStatusResponse(
        service_id=service_id,
        is_bookmarked=social_module.is_bookmarked(db, current_user, service_id),
    )


# ── Save / Unsave ────────────────────────────────────────────────────────────

@router.post("/{service_id}", response_model=BookmarkResponse)
def bookmark(
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a post. Idempotent."""
    return social_module.bookmark_post(db, current_user, service_id)


@router.delete("/{service_id}", response_model=BookmarkResponse)
def unbookmark(
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unsave a post. Idempotent."""
    return social_module.unbookmark_post(db, current_user, service_id)