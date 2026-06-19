"""
Explore module — a trending, masonry-style feed.

Ranking: a "trending" score blending engagement with recency so recent posts
with traction rise and stale posts sink even if they have high all-time totals:

    engagement = like_count + 2*comment_count + 2*rating_count
    score      = (engagement + 1) / pow(age_hours + 2, GRAVITY)

(+1 lets brand-new zero-engagement posts still surface a little; +2 on age avoids
a divide-by-zero spike in the first hour; GRAVITY tunes decay — ~1.4 is a sane
Hacker-News-ish default.)

Pagination: keyset on (score, id) within a single ordered query (score DESC,
id DESC). Score is recomputed each request from live counters (not a stored
column); seeking past the last (score, id) keeps a single request's ordering
consistent. Minor drift between requests just nudges a post a position or two —
fine for explore.

Tile buckets for the masonry grid: FEATURE (2-wide tall, rare/top), TALL,
MEDIUM, SMALL (all 1-wide). Deterministic per post so sizes don't reshuffle on
scroll.

One joined query per page (no N+1): Service ⋈ Vendor ⋈ Add_Service, LEFT JOIN
price_history (so price-less posts still appear). The score is computed in SQL
so it can drive both ORDER BY and the keyset WHERE.
"""

import base64
import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

GRAVITY = 1.4

_FEATURE_TOP_N = 2      # the top N of the first page get a FEATURE tile
_FEATURE_EVERY = 11     # ...and ~1 in N elsewhere (by id hash)


def _encode_score_cursor(score: float, sid: UUID) -> str:
    raw = f"{score:.9f}|{sid}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_score_cursor(cursor: str) -> tuple[float, str]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    score_s, sid = raw.split("|", 1)
    return float(score_s), sid


def _tile_for(service_id: str, global_rank: int) -> str:
    """Deterministic tile bucket. Top few -> FEATURE; otherwise a stable hash of
    the id spreads SMALL/MEDIUM/TALL with an occasional FEATURE."""
    if global_rank < _FEATURE_TOP_N:
        return "FEATURE"
    h = int(hashlib.md5(service_id.encode()).hexdigest(), 16)
    if h % _FEATURE_EVERY == 0:
        return "FEATURE"
    bucket = h % 10
    if bucket < 3:
        return "TALL"      # ~30%
    elif bucket < 7:
        return "MEDIUM"    # ~40%
    else:
        return "SMALL"     # ~30%


def _score_expr(Service):
    """SQLAlchemy expression for the trending score (mirrors the docstring)."""
    engagement = (
        Service.like_count
        + 2 * Service.comment_count
        + 2 * Service.rating_count
        + 1.0
    )
    age_hours = func.extract("epoch", func.now() - Service.created_at) / 3600.0
    return engagement / func.power(age_hours + 2.0, GRAVITY)


def get_explore_feed(
    db: Session,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> dict:
    """Trending posts, keyset-paginated by (score, id). ExplorePage shape:
    {items: [{post, counts, tile}], next_cursor}."""
    from app.models.service_model import Service, Add_Service, price_history
    from app.models.vendor_model import Vendor
    from app.modules.big_services_module import _build_full_response
    from app.modules.social_module import _counts_for

    limit = max(1, min(limit, 50))
    score = _score_expr(Service).label("score")

    q = (
        db.query(Service, Vendor, price_history, Add_Service, score)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .outerjoin(price_history, Service.price_history == price_history.id)
    )

    if cursor:
        c_score, c_id = _decode_score_cursor(cursor)
        # Keyset on the tuple (score, id) in (score DESC, id DESC) ordering.
        q = q.filter(
            or_(
                score < c_score,
                and_(score == c_score, Service.id < c_id),
            )
        )

    q = q.order_by(score.desc(), Service.id.desc()).limit(limit + 1)
    rows = q.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for offset, (service, vendor, ph, add_service, row_score) in enumerate(rows):
        post = _build_full_response(db, service, vendor, ph, add_service)
        global_rank = offset if cursor is None else _FEATURE_TOP_N + offset
        items.append({
            "post": post,
            "counts": _counts_for(service),
            "tile": _tile_for(str(service.id), global_rank),
        })

    next_cursor = None
    if has_more and rows:
        last_service = rows[-1][0]
        last_score = float(rows[-1][4])
        next_cursor = _encode_score_cursor(last_score, str(last_service.id))

    return {"items": items, "next_cursor": next_cursor}