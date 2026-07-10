from sqlalchemy import Column, String, UUID, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.config.db.postgresql import Base
from app.utils.mixins import TimestampMixin
import uuid
from datetime import datetime

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default = uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)


    #relationship with booking 
    users_booking  = relationship("Booking", back_populates="booking_user")

    #relationship with customer
    user_customer = relationship("customer", back_populates = "customer_user")

    #relationship with Vendor
    user_vendor = relationship("Vendor", back_populates = "vendor_user")

# ... existing User class above ...

class RefreshToken(TimestampMixin, Base):
    """
    One row per issued refresh token. We store only the SHA-256 hash of the opaque
    token (never the token itself). Rotation marks the old row revoked and links it
    to its replacement; a whole family (rotation chain from one login) shares
    family_id so presenting a revoked token can nuke the family (theft signal).
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)   # SHA-256 hex
    family_id = Column(UUID(as_uuid=True), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(tz=None))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by = Column(UUID(as_uuid=True), nullable=True)
    user_agent = Column(String, nullable=True)
    created_ip = Column(String, nullable=True)