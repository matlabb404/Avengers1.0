from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date

class Vendor(Base):
    __tablename__ = "Vendor"

    vendor_id = Column(Integer,primary_key=True,nullable=False)
    first_name = Column(String)
    last_name = Column(String, nullable=False)
    house_no= Column(String(50))
    street = Column(String(100), nullable=False)
    city = Column(String, nullable=False)
    state = Column(String(20))
    postal_code = Column(String(10), nullable=False)
    country = Column(String)
    age = Column(Date)
    business_name = Column(String)
    pictures_url = Column(String)

