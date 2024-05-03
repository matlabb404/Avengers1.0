from pydantic import BaseModel
from datetime import date
from enum import Enum

class Gender(str,Enum):
    Male = 'Male'
    Female = "Female"
    Not_Specified = "Not_Specified"

class VendorCreateBase(BaseModel):
    first_name : str
    last_name : str 
    house_no : str 
    street : str 
    city : str
    state: str 
    postal_code : str 
    country: str
    gender: Gender
    age: date
    business_name: str 
    pictures_url : str 