from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from uuid import UUID



class CustomerCreateBase(BaseModel):
    name : str
    address_1 : str
    address_2 : str
    city : str
    post_code : str
    country : str
    date_of_birth : date
    
    
class CustomerUpdate(BaseModel):
    # All optional with defaults so a partial update sends only what changes
    # (the module uses exclude_unset, so an omitted field is left untouched).
    name: Optional[str] = None
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    post_code: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    avatar_asset_id: Optional[UUID] = None   # a READY, caller-owned image asset