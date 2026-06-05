from app.config.db.postgresql import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from sqlalchemy import Column, DateTime, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID, ForeignKey, ARRAY, Float
from sqlalchemy.orm import relationship
from app.models.payment_model import Currency
from datetime import datetime, timezone

class Add_Service(Base):
   __tablename__ = "add_service"

   id = Column(String, primary_key=True)
   service_name = Column(String)
   interval_minutes = Column(Integer)
   vendor_id = Column(String)
   
   service_relation = relationship("Service", back_populates="add_service", uselist=False)

class Service(Base):
   __tablename__ = "services"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'), nullable=False)  
   price = Column(Float, nullable=True) #incase of special pricing on this in particular like promo, logic works on frontend
   price_history = Column(UUID(as_uuid=True), ForeignKey('price_history.id'), nullable=True)  
   add_service_id = Column(String, ForeignKey('add_service.id'), nullable=False)  
   # Ordered references into media_assets. Replaces the legacy image_url string
   asset_ids = Column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)
   description = Column(String, nullable=True)  

   # Define relationships
   add_service = relationship("Add_Service",uselist=False, back_populates="service_relation")

   #booking relationship
   booking = relationship("Booking",uselist=False, back_populates="service")

class price_history(Base):
   __tablename__ = "price_history"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   service_id = Column(String, ForeignKey('add_service.id'), nullable=False)  
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'), nullable=False)  
   price = Column(Float)

   # ✅ NEW - audit fields
   price_minor = Column(Integer, nullable=False, default=0)  # match Add_Service
   currency = Column(Enum(Currency), nullable=False, default=Currency.GHS)

   # Both timestamps now
   created_at = Column(
       DateTime,
       nullable=False,
       default=lambda: datetime.now(timezone.utc)
   )
   updated_at = Column(
       DateTime,
       nullable=False,
       default=lambda: datetime.now(timezone.utc),
       onupdate=lambda: datetime.now(timezone.utc)   # Auto-bumps on every UPDATE
   )