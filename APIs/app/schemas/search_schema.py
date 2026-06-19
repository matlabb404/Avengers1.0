from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class VendorHit(BaseModel):
    vendor_id: UUID
    business_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    score: float = 0.0


class ServiceHit(BaseModel):
    service_id: UUID
    add_service_id: Optional[str] = None
    service_name: Optional[str] = None
    description: Optional[str] = None
    vendor_id: UUID
    business_name: Optional[str] = None
    asset_ids: List[str] = []
    like_count: int = 0
    comment_count: int = 0
    rating_count: int = 0
    rating_avg: Optional[float] = None
    score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    vendors: List[VendorHit] = []
    services: List[ServiceHit] = []