from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date,DateTime, UUID, ForeignKey
from sqlalchemy.orm import relationship
import uuid


class Booking(Base):
    __tablename__ = "booking"

    booking_id = Column(UUID(as_uuid= True), primary_key = True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    customer_id = Column(UUID(as_uuid= True), ForeignKey('Users.id'), nullable = False)
    time_date = Column(DateTime)
    notes = Column(String(300))


    #relationship with service table
    service = relationship("Service", back_populates="booking")

    #relationship with user table
    booking_user = relationship("User",  back_populates="users")
