from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.config.db.postgresql import Base

class User(Base):
    __tablename__ = "Users"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)


    #relationship with booking

    users = relationship("Booking", back_populates = "booking_user")