from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import social_module
from app.modules.account_module import get_current_user
from app.schemas.social_schema import (
    LikeResponse,
    LikedFlagsRequest,
    LikedFlagsResponse,
)
from pydantic import BaseModel

router = APIRouter(prefix="/likes", tags=["likes"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LikeStatusResponse(BaseModel):
    service_id: UUID
    is_liked: bool


# ── Batch flags (literal path, declared first) ───────────────────────────────

@router.post("/flags", response_model=LikedFlagsResponse)
def liked_flags(
    req: LikedFlagsRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Given a list of post ids (e.g. the ids on the current feed/Discover page),
    return the subset the current user has liked — one query. The client merges
    this into the cached, count-only post data to render filled-in hearts.
    """
    response.headers["Cache-Control"] = "private, no-store"
    liked = social_module.liked_service_ids(db, current_user, req.service_ids)
    return LikedFlagsResponse(liked_ids=list(liked))


# ── Single-post status ───────────────────────────────────────────────────────

@router.get("/status/{service_id}", response_model=LikeStatusResponse)
def like_status(
    service_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, no-store"
    return LikeStatusResponse(
        service_id=service_id,
        is_liked=social_module.is_liked(db, current_user, service_id),
    )


# ── Like / Unlike ────────────────────────────────────────────────────────────

@router.post("/{service_id}", response_model=LikeResponse)
def like(
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_module.like_post(db, current_user, service_id)


@router.delete("/{service_id}", response_model=LikeResponse)
def unlike(
    service_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_module.unlike_post(db, current_user, service_id)