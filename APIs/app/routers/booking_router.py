from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Annotated
import app.modules.booking_module as booking_mdl
from app.schemas import booking_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.booking_schema import dates_to_use
import datetime
import redis ,hashlib,secrets,string

router = APIRouter(prefix="/Booking")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

times = [f"{hour:02}:{minute:02}" for hour in range(24) for minute in (0, 30)]

@router.post("/Add_booking", tags=["Booking"])
async def add_booking( book_date_dropdown: booking_schema.BookingDates, book: booking_schema.BookingSchema, db:Session=Depends(get_db),  time : str = Query(..., description="Select a time", enum=times) ):
     # Combine date and time
    timedate = f"{book_date_dropdown} {time}"
    
    # Parse the combined string into a datetime object
    #timedate = combined_datetime_str.strftime("%Y-%m-%d %H:%M")
    responce = booking_mdl.add_booking(db=db, book=book, timedate=timedate)
    return responce