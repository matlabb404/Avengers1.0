from app.config.db.postgresql import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from sqlalchemy import Column, DateTime, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID, ForeignKey, ARRAY, Float
from sqlalchemy.orm import relationship
from app.models.payment_model import Currency
from app.utils.mixins import TimestampMixin
from datetime import datetime, timezone

class Add_Service(TimestampMixin, Base):
   __tablename__ = "add_service"

   id = Column(String, primary_key=True)
   service_name = Column(String)
   interval_minutes = Column(Integer)
   vendor_id = Column(String)
   
   service_relation = relationship("Service", back_populates="add_service", uselist=False)

class Service(TimestampMixin, Base):
   __tablename__ = "services"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'), nullable=False)  
   price = Column(Float, nullable=True) #incase of special pricing on this in particular like promo, logic works on frontend
   price_history = Column(UUID(as_uuid=True), ForeignKey('price_history.id'), nullable=True)  
   add_service_id = Column(String, ForeignKey('add_service.id'), nullable=False)  
   asset_ids = Column(ARRAY(PG_UUID(as_uuid=True)), nullable=True)
   description = Column(String, nullable=True)  
   like_count = Column(Integer, nullable=False, default=0, server_default="0")
   comment_count = Column(Integer, nullable=False, default=0, server_default="0")
   rating_count = Column(Integer, nullable=False, default=0, server_default="0")
   rating_sum = Column(Integer, nullable=False, default=0, server_default="0")

   # Define relationships
   add_service = relationship("Add_Service",uselist=False, back_populates="service_relation")

   #booking relationship
   booking = relationship("Booking",uselist=False, back_populates="service")

   # ── Social relationships ──────────────────────────────────────────────
   comments = relationship(
       "Comment", back_populates="service", cascade="all, delete-orphan"
   )
   likes = relationship(
       "Like", back_populates="service", cascade="all, delete-orphan"
   )

class price_history(TimestampMixin, Base):
   __tablename__ = "price_history"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   service_id = Column(String, ForeignKey('add_service.id'), nullable=False)  
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'), nullable=False)  
   price = Column(Float)

   # ✅ NEW - audit fields
   price_minor = Column(Integer, nullable=False, default=0)  # match Add_Service
   currency = Column(Enum(Currency), nullable=False, default=Currency.GHS)