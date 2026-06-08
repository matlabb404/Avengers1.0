"""
    CRITICAL caching rules baked in here:
  - NO auth dependency. Requiring a token would make the response vary per user
    and break sharing. Discover is open.
  - region is a query-string STRING (client resolves GPS -> region name, falls
    back to profile city). Never raw coordinates — that would make every device
    a unique URL and destroy the cache hit rate.
  - per-user flags (is_liked / is_following) are deliberately absent; the client
    fills them in via POST /likes/flags and the following-status endpoint, which
    are themselves private/no-store.
  - Cache-Control: public, max-age=120. Edge-cached for 2 minutes per region+cursor.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.modules import social_module
from app.schemas.social_schema import FeedPage

router = APIRouter(prefix="/discover", tags=["discover"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=FeedPage)
def discover(
    response: Response,
    region: Optional[str] = Query(
        None,
        description="Resolved region name (e.g. 'Accra'). Omit or 'everywhere' "
                    "for the global firehose. Never send raw lat/lng.",
    ),
    limit: int = Query(20, ge=1, le=50),
    cursor: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Public, region-ranked post feed. Newest-first within the region (v1).
    Edge-cached for 2 minutes per region+cursor.
    """
    # Shared, region-scoped cache. Cloudflare keys on the full URL, so each
    # distinct (region, cursor) is its own cache entry.
    response.headers["Cache-Control"] = "public, max-age=120"
    return social_module.get_discover_feed(
        db, region=region, limit=limit, cursor=cursor
    )