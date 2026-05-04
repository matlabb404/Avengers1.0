from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, Boolean, Time, Date, Enum, UUID, ForeignKey, JSON, UniqueConstraint
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
    days = Column(JSON) #day(monday,tuesday) and times worked everyweek
    start_time = Column(Time)
    end_time = Column(Time)
    capacity = Column(Integer)

# weekly rules ✅
# working hours ✅
# capacity ✅

    schedules = relationship("Vendor", back_populates = "schedule")

class ScheduleException(Base):
    __tablename__ = "schedule_exceptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    vendor_id = Column(UUID(as_uuid=True), ForeignKey("Vendor.vendor_id"))

    date = Column(Date, nullable=False)

    # optional overrides
    is_closed = Column(Boolean, default=False)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    capacity = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)

# Full-day holiday	✅ is_closed=True
# Late opening	✅ override start_time
# Early closing	✅ override end_time
# Special busy day	✅ override capacity
# Multiple exceptions	✅ multiple rows

    vendor = relationship("Vendor")
    __table_args__ = (
        UniqueConstraint("vendor_id", "date", name="unique_exception_per_day"),
    )