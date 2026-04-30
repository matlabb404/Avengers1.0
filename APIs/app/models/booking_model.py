from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, DateTime, UUID, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
import uuid

class Booking(Base):
    __tablename__ = "booking"

    booking_id = Column(UUID(as_uuid= True), primary_key = True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    user_id = Column(UUID(as_uuid= True), ForeignKey('users.id'), nullable = False)
    time_date = Column(DateTime)
    notes = Column(String(300))
    status = Column(String, default="init") #init, pending(paid), cancelled, completed

    #relationship with service table
    service = relationship("Service", back_populates="booking")

    #relationship with user table
    booking_user = relationship("User",  back_populates="users_booking")

    __table_args__ = (
        UniqueConstraint("service_id", "time_date", "user_id", name="unique_user_booking"),
        Index("idx_booking_service_time", "service_id", "time_date"),
    )

class Slot(Base):
    __tablename__ = "booking_slots"

    id = Column(UUID(as_uuid= True), primary_key = True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    time = Column(DateTime, index=True)
    capacity = Column(Integer)
    booked = Column(Integer, default=0)


# Schedule = rules
# Slots = generated (or virtual)
# Bookings = actual usage