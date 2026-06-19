"""
Explore feed schemas. Dedicated ExplorePage shape (distinct from the feeds),
reusing the post + counts types from social_schema but adding the `tile` bucket
that drives the masonry grid.

Place in app/schemas/explore_schema.py
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.social_schema import EngagementCounts, FullServiceResponse


class TileBucket(str, Enum):
    """Masonry tile size the client should render for this post."""
    SMALL = "SMALL"     # 1-wide, short
    MEDIUM = "MEDIUM"   # 1-wide, medium
    TALL = "TALL"       # 1-wide, tall
    FEATURE = "FEATURE" # 2-wide, tall (reserved for top-ranked / occasional)


class ExploreItem(BaseModel):
    post: FullServiceResponse
    counts: EngagementCounts
    tile: TileBucket = TileBucket.MEDIUM


class ExplorePage(BaseModel):
    """A page of trending explore items plus an opaque (score,id) cursor."""
    items: List[ExploreItem] = Field(default_factory=list)
    next_cursor: Optional[str] = None