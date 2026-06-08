from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import social_module
from app.modules.account_module import get_current_user
from app.schemas.social_schema import (
    CommentCreate,
    CommentEdit,
    CommentOut,
    CommentPage,
    DeleteResponse,
)

router = APIRouter(prefix="/comments", tags=["comments"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Replies (literal-suffixed param path) ────────────────────────────────────

@router.get("/{comment_id}/replies", response_model=CommentPage)
def list_replies(
    comment_id: UUID,
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "private, no-store"
    result = social_module.list_replies(db, comment_id, limit=limit, cursor=cursor)
    items = [
        social_module.comment_to_out(db, c, include_reply_count=False)
        for c in result["items"]
    ]
    return {"items": items, "next_cursor": result["next_cursor"]}


# ── Edit (literal prefix) ────────────────────────────────────────────────────

@router.put("/edit/{comment_id}", response_model=CommentOut)
def edit_comment(
    comment_id: UUID,
    payload: CommentEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = social_module.edit_comment(
        db, current_user, comment_id, body=payload.body, stars=payload.stars
    )
    return social_module.comment_to_out(db, row)


# ── Create ───────────────────────────────────────────────────────────────────

@router.post("/{service_id}", response_model=CommentOut)
def add_comment(
    service_id: UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = social_module.add_comment(
        db,
        current_user,
        service_id,
        body=payload.body,
        stars=payload.stars,
        parent_id=payload.parent_id,
        booking_id=payload.booking_id,
    )
    return social_module.comment_to_out(db, row)


# ── List top-level comments ──────────────────────────────────────────────────

@router.get("/{service_id}", response_model=CommentPage)
def list_comments(
    service_id: UUID,
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "private, no-store"
    result = social_module.list_comments(db, service_id, limit=limit, cursor=cursor)
    items = [social_module.comment_to_out(db, c) for c in result["items"]]
    return {"items": items, "next_cursor": result["next_cursor"]}


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{comment_id}", response_model=DeleteResponse)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_module.delete_comment(db, current_user, comment_id)