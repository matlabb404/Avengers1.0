"""
app/modules/location_module.py

Business logic for the vendor location feature:
  - upsert_vendor_location: insert or overwrite a vendor's single location row
  - get_vendor_location:    read a vendor's own location (settings read-back)
  - list_vendor_pins:       every pinned vendor for the near-me map

vendor_id is the UUID "Vendor".vendor_id. The near-me join reads business_name
as the display name.
"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.location_model import VendorLocation
from app.schemas.location_schema import LocationIn, VendorPin


def upsert_vendor_location(
    db: Session,
    vendor_id: UUID,
    data: LocationIn,
    commit: bool = True,
) -> VendorLocation:
    """Create the vendor's location row, or overwrite it if one exists. One row
    per vendor, so an edit is just an overwrite. The DB trigger keeps geog in
    sync, so we only ever write lat/lng and the text fields here."""
    loc = (
        db.query(VendorLocation)
        .filter(VendorLocation.vendor_id == vendor_id)
        .one_or_none()
    )
    if loc is None:
        loc = VendorLocation(vendor_id=vendor_id)
        db.add(loc)

    loc.latitude = data.latitude
    loc.longitude = data.longitude
    loc.address_line1 = data.address_line1
    loc.city = data.city
    loc.region = data.region
    loc.country = data.country or "Ghana"
    loc.digital_address = data.digital_address
    loc.map_link = data.map_link

    if commit:
        db.commit()
        db.refresh(loc)   # reload trigger/mixin-updated fields
    else:
        db.flush()
    return loc


def get_vendor_location(db: Session, vendor_id: UUID) -> Optional[VendorLocation]:
    """A vendor's own saved location, or None if they have not pinned yet."""
    return (
        db.query(VendorLocation)
        .filter(VendorLocation.vendor_id == vendor_id)
        .one_or_none()
    )


def list_vendor_pins(
    db: Session,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None,
) -> List[VendorPin]:
    """Every vendor that has a location, as map pins.

    v1 returns all pinned vendors. lat/lng/radius_km are accepted now for a
    stable client contract but ignored until the radius search ships. When it
    does, this becomes a WHERE on the dormant geog column, for example:

        WHERE ST_DWithin(
            vl.geog,
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography,
            :radius_m
        )
        ORDER BY vl.geog <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography
    """
    sql = text(
        '''
        SELECT vl.vendor_id,
               v.business_name AS name,
               vl.latitude,
               vl.longitude,
               vl.city,
               vl.region
        FROM vendor_location vl
        JOIN "Vendor" v ON v.vendor_id = vl.vendor_id
        ORDER BY name
        '''
    )
    rows = db.execute(sql).mappings().all()
    return [VendorPin(**row) for row in rows]