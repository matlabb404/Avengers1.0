from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date,DateTime

class customer(Base):
    __tablename__ = "customer"

    customer_id = Column(Integer,primary_key=True,nullable=False)
    name = Column(String(25))
    address_1 = Column(String(100), nullable=False)
    address_2 = Column(String(100))
    city = Column(String, nullable=False)
    post_code = Column(String(10), nullable=False)
    country = Column(String)
    date_of_birth = Column(Date)
    last_edited = Column(DateTime,nullable=False)

