from pydantic import BaseModel, UUID4, HttpUrl, Field
from uuid import UUID
from datetime import date
from enum import Enum
from typing import Optional


class ServiceSchema(BaseModel):
    id: UUID
    vendor_id: UUID # Foreign key to the vendors table
    price: int
    add_service_id: UUID  # Foreign key to the add_services table
    
    
class ServiceUpdate(BaseModel):
    price: Optional[float] = Field(None, title="Price")
    vendor_id: Optional[str] = Field(None, title="Vendor ID")
    add_service_id: Optional[str] = Field(None, title="Service ID")