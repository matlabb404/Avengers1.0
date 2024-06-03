from sqlalchemy import Column, Integer, String, UUID
from sqlalchemy.orm import relationship
from app.config.db.postgresql import Base
import uuid

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default = uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)


    #relationship with booking 
    users_booking  = relationship("Booking", back_populates="booking_user")

    #relationship with customer

    user_customer = relationship("customer", back_populates = "customer_user")




