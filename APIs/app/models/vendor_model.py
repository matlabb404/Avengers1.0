from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID, ForeignKey
from app.schemas.vendor_Schema import Gender
import uuid 
from sqlalchemy.orm import relationship

class Vendor(Base):
    __tablename__ = "Vendor"

    vendor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid= True),ForeignKey('users.id'), nullable=False)
    vendor_email = Column(String)
    first_name = Column(String)
    last_name = Column(String, nullable=False)
    house_no= Column(String(50))
    street = Column(String(100), nullable=False)
    city = Column(String, nullable=False)
    state = Column(String(20))
    postal_code = Column(String(10), nullable=False)
    country = Column(String)
    gender = Column(Enum(Gender), default=Gender.Male)
    date_of_birth = Column(Date)
    business_name = Column(String)
    phone_no = Column(String(50))

    vendor_details = relationship("Vendor_Details", uselist=False, back_populates="vendor")

    vendor_user = relationship("User", back_populates = "user_vendor")
    
    schedule = relationship("Scheduling_", back_populates = "schedules")

class Vendor_Details(Base):
    __tablename__= "Vendor_Details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id_details = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'))
    description = Column(String)
    picture_url = Column(String)
    review = Column(String)

    vendor = relationship("Vendor", back_populates="vendor_details")

class Scheduling_(Base):
    __tablename__= "Schedule"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'))
    days = Column(String) #day(monday,tuesday) and times
    exceptions = Column(Date)

    schedules = relationship("Vendor", back_populates = "schedule")