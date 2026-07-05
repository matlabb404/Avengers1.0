from pydantic import BaseModel
from uuid import UUID
import calendar
import datetime
from enum import Enum
from app.schemas.big_services_schema import FullServiceResponse

datess = {}
dates_to_use = []

def all_days(year):
    if calendar.isleap(year):
        days_for_months = calendar.mdays
        days_for_months[2] = 29
    else :
        days_for_months = calendar.mdays
        days_for_months[2] = 28
    for i in range(1,13,1):
        for j in range(1,days_for_months[i]+1,1):
            date = datetime.date(year, i, j)
            dates_to_use.append(date.strftime("%A")+","+ str(date))
    for seen, bookdates in enumerate(dates_to_use, start = 1):
        datess[bookdates] = str(bookdates)

today = datetime.date.today()
all_days(today.year)

class BookingSchema(BaseModel):
    service_id: UUID
    notes: str
    #time_date: datetime.datetime

# Dynamically create an enumeration for the datesclass BookingDates(str):
    #for i in range(len(dates_to_use)):
    #    dates_to_use[i][:12] = dates_to_use[i]

BookingDates = Enum('BookingDates', {dates_to_use[i]: dates_to_use[i] for i in range(len(dates_to_use))})


class BookingRespone(BaseModel):
    booking_id: str
    service_id: UUID
    user_id: UUID
    business_name: str
    service_name: str
    price_minor_at_booking: int
    currency_at_booking: str
    time_date: datetime.datetime      # was booking_time
    notes: str
    status: str | None = None
    payment_status: str | None = None

class BookingCreate(BaseModel):
    service_id: UUID
    notes: str | None = None
    booking_time: datetime.datetime

class BookingDetailResponse(BaseModel):
    booking: BookingRespone          # your existing booking schema
    service: FullServiceResponse
    payment_reference: str | None = None

    class Config:
        from_attributes = True