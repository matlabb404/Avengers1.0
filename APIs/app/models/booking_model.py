from datetime import datetime, timezone

from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, DateTime, UUID, ForeignKey, UniqueConstraint, Index, Enum
from sqlalchemy.orm import relationship
from app.models.payment_model import Currency, PaymentStatus
from app.utils.mixins import TimestampMixin
import uuid
import enum

class BookingStatus(str, enum.Enum):
    INIT = "init"                            # Just created, no payment yet
    PENDING = "pending"                      # Awaiting Payment
    CONFIRMED = "confirmed"                  # Paid + booking locked in
    CANCELLED = "cancelled"
    COMPLETED = "completed"                  # Service has been delivered

class Booking(TimestampMixin, Base):
    __tablename__ = "booking"

    booking_id = Column(UUID(as_uuid= True), primary_key = True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    user_id = Column(UUID(as_uuid= True), ForeignKey('users.id'), nullable = False)
    time_date = Column(DateTime)
    notes = Column(String(300))
    status = Column(Enum(BookingStatus), nullable=False, default=BookingStatus.INIT) #init, pending(paid), cancelled, completed

    # ✅ NEW - Price snapshot at booking time (immutable record)
    price_minor_at_booking = Column(Integer, nullable=False, default=0)
    currency_at_booking = Column(Enum(Currency), nullable=False, default=Currency.GHS)
    
    # ✅ NEW - Denormalized payment status for fast queries
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    #relationship with service table
    service = relationship("Service", back_populates="booking")

    #relationship with user table
    booking_user = relationship("User",  back_populates="users_booking")

    #relationship with payments table
    payments = relationship("Payment", back_populates="booking")  

    # The one rating-comment tied to this booking (a rating requires a completed
    # booking; uq_comment_rating_per_booking guarantees at most one). uselist=False
    # because it's 0-or-1. Cascade so deleting a booking removes its rating.
    rating = relationship(
        "Comment",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("service_id", "time_date", "user_id", name="unique_user_booking"),
        Index("idx_booking_service_time", "service_id", "time_date"),
        Index("idx_booking_payment_status", "payment_status"),  
    )

class Slot(TimestampMixin, Base):
    __tablename__ = "booking_slots"

    id = Column(UUID(as_uuid= True), primary_key = True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    time = Column(DateTime, index=True)
    capacity = Column(Integer)
    booked = Column(Integer, default=0)


# Schedule = rules
# Slots = generated (or virtual)
# Bookings = actual usage#