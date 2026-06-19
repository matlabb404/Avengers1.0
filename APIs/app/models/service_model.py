from app.config.db.postgresql import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, TSVECTOR
import uuid
from sqlalchemy import Column, Computed, Integer, String, Index, Enum, UUID, ForeignKey, ARRAY, Float
from sqlalchemy.orm import relationship
from app.models.payment_model import Currency
from app.utils.mixins import TimestampMixin

class Add_Service(TimestampMixin, Base):
   __tablename__ = "add_service"

   id = Column(String, primary_key=True)
   service_name = Column(String)
   interval_minutes = Column(Integer)
   vendor_id = Column(String)
   
   # ── Search: full-text vector over the service name (generated/STORED) ──
   search_tsv = Column(
       TSVECTOR,
       Computed(
           "setweight(to_tsvector('simple', coalesce(service_name, '')), 'A')",
           persisted=True,
       ),
       nullable=True,
   )

   service_relation = relationship("Service", back_populates="add_service", uselist=False)

   __table_args__ = (
       Index("add_service_search_tsv_gin", "search_tsv", postgresql_using="gin"),
       Index(
           "add_service_name_trgm", "service_name",
           postgresql_using="gin", postgresql_ops={"service_name": "gin_trgm_ops"},
       ),
   )

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

   # ── Search: full-text vector over the post description (generated/STORED) ──
   search_tsv = Column(
       TSVECTOR,
       Computed(
           "setweight(to_tsvector('simple', coalesce(description, '')), 'B')",
           persisted=True,
       ),
       nullable=True,
   )

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

   __table_args__ = (
       Index("services_search_tsv_gin", "search_tsv", postgresql_using="gin"),
       Index(
           "services_description_trgm", "description",
           postgresql_using="gin", postgresql_ops={"description": "gin_trgm_ops"},
       ),
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