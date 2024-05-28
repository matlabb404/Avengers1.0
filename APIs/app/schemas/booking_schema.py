from pydantic import BaseModel, UUID4, HttpUrl, Field
from uuid import UUID
import calendar
import datetime
from enum import Enum
from typing import Optional

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
    booking_id: UUID
    service_id: UUID
    customer_id: UUID
    notes: str
    #time_date: datetime.datetime

# Dynamically create an enumeration for the datesclass BookingDates(str):
    #for i in range(len(dates_to_use)):
    #    dates_to_use[i][:12] = dates_to_use[i]

BookingDates = Enum('BookingDates', {f'DATE_{i}': dates_to_use[i] for i in range(len(dates_to_use))})