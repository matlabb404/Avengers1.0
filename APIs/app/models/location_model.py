"""
app/models/location_model.py

SQLAlchemy model for the vendor_location table (see 20261006_vendor_location.sql).
One row per vendor: vendor_id is the primary key and the FK to "Vendor". The
geography column `geog` is maintained by a DB trigger from latitude/longitude and
is intentionally NOT mapped here, so PostGIS stays out of Python until the radius
search ships.

Reminder: there is no app/models/__init__.py, so import this model explicitly
wherever the other models are registered:

    from app.models.location_model import VendorLocation
"""

from sqlalchemy import Column, Float, Text, ForeignKey, UUID

from app.config.db.postgresql import Base
from app.utils.mixins import TimestampMixin


class VendorLocation(TimestampMixin, Base):
    __tablename__ = "vendor_location"

    # One row per vendor; vendor_id is both PK and FK. The upsert in
    # location_module overwrites on edit.
    vendor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("Vendor.vendor_id", ondelete="CASCADE"),
        primary_key=True,
    )

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Typed address fields, all optional.
    address_line1 = Column(Text)
    city = Column(Text)
    region = Column(Text)
    country = Column(Text, nullable=False, server_default="Ghana")
    digital_address = Column(Text)   # GhanaPost GPS, e.g. GA-123-4567
    map_link = Column(Text)          # optional pasted convenience link, never relied on


    def __repr__(self) -> str:
        return (
            f"<VendorLocation vendor_id={self.vendor_id} "
            f"lat={self.latitude} lng={self.longitude}>"
        )