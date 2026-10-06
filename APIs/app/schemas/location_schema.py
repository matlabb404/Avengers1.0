"""
app/schemas/location_schema.py

Pydantic DTOs for the vendor location feature (Pydantic v2).
vendor_id is a UUID, matching "Vendor".vendor_id.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# Ghana bounding box. Mirrors the DB CHECK constraints so a bad pin is rejected
# at the API edge with a clear 422, not a 500.
LAT_MIN, LAT_MAX = 4.5, 11.2
LNG_MIN, LNG_MAX = -3.3, 1.3


def _clean(v: Optional[str]) -> Optional[str]:
    """Trim whitespace, turn blank strings into None."""
    if v is None:
        return None
    v = v.strip()
    return v or None


class LocationIn(BaseModel):
    """Vendor saves or updates their location. Only lat/lng are required; the
    client sends them from the dropped pin, and the vendor types the rest."""

    latitude: float = Field(..., description="WGS84 latitude")
    longitude: float = Field(..., description="WGS84 longitude")

    address_line1: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = "Ghana"
    digital_address: Optional[str] = None   # GhanaPost GPS, e.g. GA-123-4567
    map_link: Optional[str] = None          # optional pasted convenience link

    @field_validator("latitude")
    @classmethod
    def _lat_bounds(cls, v: float) -> float:
        if not (LAT_MIN <= v <= LAT_MAX):
            raise ValueError(f"latitude must be within Ghana ({LAT_MIN} to {LAT_MAX})")
        return v

    @field_validator("longitude")
    @classmethod
    def _lng_bounds(cls, v: float) -> float:
        if not (LNG_MIN <= v <= LNG_MAX):
            raise ValueError(f"longitude must be within Ghana ({LNG_MIN} to {LNG_MAX})")
        return v

    @field_validator(
        "address_line1", "city", "region", "country", "digital_address", "map_link"
    )
    @classmethod
    def _trim(cls, v: Optional[str]) -> Optional[str]:
        return _clean(v)


class LocationOut(BaseModel):
    """A vendor's own saved location, for read-back on the settings screen."""

    vendor_id: UUID
    latitude: float
    longitude: float
    address_line1: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    digital_address: Optional[str] = None
    map_link: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VendorPin(BaseModel):
    """One pin for the near-me map. The client needs only lat/lng plus a name to
    drop the marker and build the ride/maps deep links; city/region are for the
    marker's label sheet."""

    vendor_id: UUID
    name: str                 # vendor business_name, joined from "Vendor"
    latitude: float
    longitude: float
    city: Optional[str] = None
    region: Optional[str] = None

    class Config:
        from_attributes = True