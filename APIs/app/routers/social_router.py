from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.models.account_model import User
from app.modules import social_module
from app.modules.account_module import get_current_user
from app.schemas.social_schema import SocialFlagsRequest, SocialFlagsResponse

router = APIRouter(prefix="/social", tags=["social"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/flags", response_model=SocialFlagsResponse)
def social_flags(
    req: SocialFlagsRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Per-user flags for a page of posts: which are liked, which are saved — one
    round trip for the whole page.

    This is the companion to the edge-cached feeds (Discover / Explore / vendor
    posts), which deliberately carry NO per-user fields so they can be shared.
    The client fetches counts from the feed and flags from here, then merges.

    Replaces the old liked-only POST /likes/flags.
    """
    response.headers["Cache-Control"] = "private, no-store"
    return social_module.social_flags(db, current_user, req.service_ids)