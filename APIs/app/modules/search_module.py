"""
Search module — blended trigram (typo-tolerant) + full-text (relevance) search
across Vendors and Services in one call.

Scoring per row: GREATEST(similarity(text, q), ts_rank(search_tsv, query)).
- similarity() catches typos / partial spellings ("braed" -> "bread braiding").
- ts_rank() rewards proper keyword matches and respects the A/B/C weights set
  on the generated tsvector columns.

Requires pg_trgm + the generated tsvector columns + GIN indexes (created via the
model definitions). The trigram match operator is a single `%`; with SQLAlchemy
text() and named (:q) params it is written literally as `%` (NOT `%%`).
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


# A small floor so near-zero fuzzy noise doesn't flood results.
_MIN_SCORE = 0.08


def search_vendors(db: Session, q: str, limit: int = 20) -> list[dict]:
    """Vendors ranked by blended trigram + full-text score."""
    sql = text(
        """
        SELECT
            v.vendor_id,
            v.business_name,
            v.first_name,
            v.last_name,
            v.city,
            v.country,
            GREATEST(
                similarity(coalesce(v.business_name, ''), :q),
                similarity(coalesce(v.city, ''), :q),
                ts_rank(v.search_tsv, plainto_tsquery('simple', :q))
            ) AS score
        FROM "Vendor" v
        WHERE
            v.search_tsv @@ plainto_tsquery('simple', :q)
            OR coalesce(v.business_name, '') % :q
            OR coalesce(v.city, '') % :q
        ORDER BY score DESC, v.business_name ASC
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"q": q, "limit": limit}).mappings().all()
    return [
        {
            "vendor_id": r["vendor_id"],
            "business_name": r["business_name"],
            "first_name": r["first_name"],
            "last_name": r["last_name"],
            "city": r["city"],
            "country": r["country"],
            "score": float(r["score"] or 0.0),
        }
        for r in rows
        if (r["score"] or 0.0) >= _MIN_SCORE
    ]


def search_services(db: Session, q: str, limit: int = 20) -> list[dict]:
    """
    Services ranked by blended score over the service NAME (add_service) and the
    post DESCRIPTION (services). Joins Vendor + add_service so each result can
    render a full row.
    """
    sql = text(
        """
        SELECT
            s.id            AS service_id,
            s.add_service_id,
            a.service_name,
            s.description,
            s.add_vendor_id AS vendor_id,
            v.business_name,
            s.asset_ids,
            s.like_count,
            s.comment_count,
            s.rating_count,
            s.rating_sum,
            GREATEST(
                similarity(coalesce(a.service_name, ''), :q),
                similarity(coalesce(s.description, ''), :q),
                ts_rank(a.search_tsv, plainto_tsquery('simple', :q)),
                ts_rank(s.search_tsv, plainto_tsquery('simple', :q))
            ) AS score
        FROM services s
        JOIN add_service a ON s.add_service_id = a.id
        JOIN "Vendor" v ON s.add_vendor_id = v.vendor_id
        WHERE
            a.search_tsv @@ plainto_tsquery('simple', :q)
            OR s.search_tsv @@ plainto_tsquery('simple', :q)
            OR coalesce(a.service_name, '') % :q
            OR coalesce(s.description, '') % :q
        ORDER BY score DESC, a.service_name ASC
        LIMIT :limit
        """
    )
    rows = db.execute(sql, {"q": q, "limit": limit}).mappings().all()
    out = []
    for r in rows:
        if (r["score"] or 0.0) < _MIN_SCORE:
            continue
        rating_count = r["rating_count"] or 0
        rating_sum = r["rating_sum"] or 0
        out.append(
            {
                "service_id": r["service_id"],
                "add_service_id": r["add_service_id"],
                "service_name": r["service_name"],
                "description": r["description"],
                "vendor_id": r["vendor_id"],
                "business_name": r["business_name"],
                "asset_ids": r["asset_ids"] or [],
                "like_count": r["like_count"] or 0,
                "comment_count": r["comment_count"] or 0,
                "rating_count": rating_count,
                "rating_avg": (round(rating_sum / rating_count, 2) if rating_count > 0 else None),
                "score": float(r["score"] or 0.0),
            }
        )
    return out


def search_all(db: Session, q: str, type_: str = "all", limit: int = 20) -> dict:
    """
    Unified search. `type_` is one of: all | vendors | services.
    Returns {"vendors": [...], "services": [...]} (empty list for the omitted type).
    """
    q = (q or "").strip()
    if not q:
        return {"vendors": [], "services": []}

    vendors = search_vendors(db, q, limit) if type_ in ("all", "vendors") else []
    services = search_services(db, q, limit) if type_ in ("all", "services") else []
    return {"vendors": vendors, "services": services}