from pydantic import BaseModel
from datetime import date


class VendorCreateBase(BaseModel):
    first_name : str
    last_name : str 
    house_no : str 
    street : str 
    city : str
    state: str 
    postal_code : str 
    country: str 
    age: date
    business_name: str 
    pictures_url : str 