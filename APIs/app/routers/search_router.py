"""
Search router — GET /search?q=&type=&limit=
Public (no auth required); results are not user-specific. Edge-cacheable briefly.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.modules import search_module
from app.schemas.search_schema import SearchResponse, VendorHit, ServiceHit

router = APIRouter(prefix="/search", tags=["Search"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("", response_model=SearchResponse)
def search(
    response: Response,
    q: str = Query("", description="Search query"),
    type: str = Query("all", pattern="^(all|vendors|services)$"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Blended trigram + full-text search across vendors and services."""
    response.headers["Cache-Control"] = "public, max-age=30"
    result = search_module.search_all(db, q=q, type_=type, limit=limit)
    return SearchResponse(
        query=q.strip(),
        vendors=[VendorHit(**v) for v in result["vendors"]],
        services=[ServiceHit(**s) for s in result["services"]],
    )