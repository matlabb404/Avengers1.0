from app.config.db.postgresql import Base
import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, Boolean, text, Date, Enum, UUID, ForeignKey
from sqlalchemy.orm import relationship
from app.schemas.services_schema import ServicesDropDownOption


class Add_Service(Base):
   __tablename__ = "add_service"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   service_name = Column(Enum(ServicesDropDownOption))
   
<<<<<<< Updated upstream
<<<<<<< Updated upstream
   service_relation = relationship("Service", back_populates="add_service", uselist=False)


class Service(Base):
   __tablename__ = "services"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.vendor_id'), nullable=False)  
   price = Column(Integer)  
   add_service_id = Column(UUID(as_uuid=True), ForeignKey('add_service.id'), nullable=False)  
   
   # Define relationships
   add_service = relationship("Add_Service",uselist=False, back_populates="service_relation")

   #booking relationship
   booking = relationship("Booking",uselist=False, back_populates="service")
=======
   service = relationship("Service", back_populates="service", uselist=False)

>>>>>>> Stashed changes

=======
   service = relationship("Service", back_populates="service", uselist=False)


>>>>>>> Stashed changes
class Service(Base):
   __tablename__ = "services"

   id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
   add_vendor_id = Column(UUID(as_uuid=True), ForeignKey('Vendor.id'), nullable=False)  
   price = Column(Integer)  
   add_service_id = Column(UUID(as_uuid=True), ForeignKey('add_service.id'), nullable=False)  
   
   # Define relationships
   vendor = relationship("Vendor", back_populates="services")
   service = relationship("AddService", back_populates="services")