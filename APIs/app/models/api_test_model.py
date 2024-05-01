from app.config.db.postgresql import Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text

class Test(Base):
    __tablename__ = "testdata"

    id = Column(Integer,primary_key=True,nullable=False)
    title = Column(String,nullable=False)