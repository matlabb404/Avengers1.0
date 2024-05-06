from app.config.db.postgresql import Base
import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID

class Add_Service(Base):
   __tablename__ = "add_service"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   service_name = Column(String)

