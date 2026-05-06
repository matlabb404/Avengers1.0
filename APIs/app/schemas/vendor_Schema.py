from pydantic import BaseModel, UUID4, Field
from uuid import UUID
from datetime import date, time
from enum import Enum
from typing import List, Optional

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
    service_id: str

class ScheduleBase(BaseModel):
    service_id: str = "all"  # "all" or specific UUID
    days: List[str] = Field(..., description="['mon', 'tue', 'wed', ...]")
    start_time: time
    end_time: time
    capacity: int = Field(ge=1, description="Max bookings per slot")
    interval_minutes: int = Field(30, ge=5, description="Slot duration in minutes")
    walk_in_available: bool = False

class ScheduleCreate(ScheduleBase):
    pass

class ScheduleUpdate(BaseModel):
    days: Optional[List[str]] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    capacity: Optional[int] = None
    interval_minutes: Optional[int] = None
    walk_in_available: Optional[bool] = None

class ScheduleResponse(ScheduleBase):
    id: UUID4
    schedule_vendor_id: UUID4
    
    class Config:
        from_attributes = True

class ExceptionBase(BaseModel):
    service_id: str = "all"
    date: date
    is_closed: bool = False
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    capacity: Optional[int] = None
    walk_in_available: Optional[bool] = None
    reason: Optional[str] = None

class ExceptionCreate(ExceptionBase):
    pass

class ExceptionResponse(ExceptionBase):
    id: UUID4
    vendor_id: UUID4
    
    class Config:
        from_attributes = True