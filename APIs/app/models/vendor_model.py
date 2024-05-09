from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID, ForeignKey
from app.schemas.vendor_Schema import Gender
import uuid 
from sqlalchemy.orm import relationship

class Vendor(Base):
    __tablename__ = "Vendor"

    vendor_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String)
    last_name = Column(String, nullable=False)
    house_no= Column(String(50))
    street = Column(String(100), nullable=False)
    city = Column(String, nullable=False)
    state = Column(String(20))
    postal_code = Column(String(10), nullable=False)
    country = Column(String)
    gender = Column(Enum(Gender), default=Gender.Male)
    age = Column(Date)
    business_name = Column(String)
    phone_no = Column(String(50))

    vendor_details = relationship("Vendor_Details", uselist=False, back_populates="vendor")


class Vendor_Details(Base):
    __tablename__= "Vendor_Details"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id_details = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'))
    description = Column(String)
    picture_url = Column(String)
    review = Column(String)

    vendor = relationship("Vendor", back_populates="vendor_details")
