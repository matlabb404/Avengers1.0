from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional



class CustomerCreateBase(BaseModel):
    name : str
    address_1 : str
    address_2 : str
    city : str
    post_code : str
    country : str
    date_of_birth : date
    last_edited: datetime = None  # Default value is None
    
    
class CustomerUpdate(BaseModel):
    name: Optional[str]
    address_1: Optional[str] 
    address_2: Optional[str] 
    city: Optional[str] 
    post_code: Optional[str] 
    country: Optional[str] 
    date_of_birth: Optional[date] 