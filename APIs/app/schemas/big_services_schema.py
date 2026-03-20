from pydantic import BaseModel, UUID4, HttpUrl, Field
from uuid import UUID
from datetime import date
from enum import Enum
from typing import Optional    
    
class ServiceUpdate(BaseModel):
    price: Optional[float] = Field(None, title="Price")
    price_history: Optional[UUID] = Field(None, title="Price History ID")
    vendor_id: Optional[str] = Field(None, title="Vendor ID")
    add_service_id: Optional[str] = Field(None, title="Service ID")
    description: Optional[str] = Field(None, title="Description")
    image_url: Optional[list[str]] = Field(None, title="Image URLs")