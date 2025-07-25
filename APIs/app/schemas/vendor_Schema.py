from pydantic import BaseModel, UUID4, HttpUrl
from uuid import UUID
from datetime import date
from enum import Enum
from typing import List

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
    date_of_birth: date
    business_name: str 
 

class VendorDetailsCreateBase(BaseModel):
    description : str
    picture_url : str
    review : str

class Scheduling(BaseModel):
    days : List[str]
    exceptions : List[date]