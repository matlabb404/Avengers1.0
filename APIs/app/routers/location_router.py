"""
app/routers/location_router.py

Endpoints for the vendor location feature:
  PUT  /location/me       vendor saves/overwrites their location
  GET  /location/me       vendor reads their own location
  GET  /location/nearby   every pinned vendor, as map pins
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config.db.postgresql import SessionLocal
from app.modules.account_module import get_current_user
from app.models.account_model import User
from app.schemas.location_schema import LocationIn, LocationOut, VendorPin
from app.modules import location_module, vendor_module

router = APIRouter(prefix="/location", tags=["location"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _current_vendor_id(db: Session, current_user: User) -> UUID:
    """Resolve the signed-in user's vendor_id, or 403 if they are not a vendor."""
    vendor = vendor_module.get_current_vendor(current_user.id, db=db)
    if vendor is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a vendor")
    return vendor.vendor_id


@router.put("/me", response_model=LocationOut)
def save_my_location(
    data: LocationIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or overwrite the signed-in vendor's location. Ghana bounds are
    enforced by the LocationIn validators, so an out-of-range pin returns 422."""
    vendor_id = _current_vendor_id(db, current_user)
    return location_module.upsert_vendor_location(db, vendor_id, data)


@router.get("/me", response_model=LocationOut)
def get_my_location(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The signed-in vendor's own location. 404 if they have not pinned yet.
    If the client prefers 200 with an empty body, change response_model to
    Optional[LocationOut] and return the None directly instead of raising."""
    vendor_id = _current_vendor_id(db, current_user)
    loc = location_module.get_vendor_location(db, vendor_id)
    if loc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no location set")
    return loc


@router.get("/nearby", response_model=List[VendorPin])
def nearby_vendors(
    lat: Optional[float] = Query(None, description="viewer latitude (ignored in v1)"),
    lng: Optional[float] = Query(None, description="viewer longitude (ignored in v1)"),
    radius_km: Optional[float] = Query(None, ge=0, description="ignored in v1; radius seam"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every vendor that has pinned a location. lat/lng/radius_km are accepted
    for a stable client contract but ignored until the radius search ships."""
    return location_module.list_vendor_pins(db, lat=lat, lng=lng, radius_km=radius_km)