from app.config.db.postgresql import Base
import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID
from app.schemas.vendor_Schema import Gender

class Vendor(Base):
    __tablename__ = "Vendor"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

