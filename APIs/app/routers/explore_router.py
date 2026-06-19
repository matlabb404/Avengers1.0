"""
Explore router — GET /explore?limit=&cursor=

A trending, masonry-style feed. Public (no per-user fields), lightly cacheable.

Mount in main.py:  app.include_router(explore_router.router)
"""

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.modules import explore_module
from app.schemas.explore_schema import ExplorePage

router = APIRouter(prefix="/explore", tags=["Explore"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=ExplorePage)
def explore(
    response: Response,
    limit: int = Query(20, ge=1, le=50),
    cursor: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Trending posts for the masonry explore grid, keyset-paginated by score."""
    response.headers["Cache-Control"] = "public, max-age=30"
    return explore_module.get_explore_feed(db, limit=limit, cursor=cursor)