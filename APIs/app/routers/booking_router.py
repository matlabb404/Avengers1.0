from fastapi import APIRouter, Depends, Query
from uuid import UUID
from typing import Annotated
import app.modules.booking_module as booking_mdl
from app.schemas import booking_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.booking_schema import dates_to_use
from app.models.account_model import User
from app.modules.account_module import get_current_user
import datetime
from datetime import datetime as dtme
import redis ,hashlib,secrets,string

router = APIRouter(prefix="/Booking")


redis_client = redis.Redis(host='localhost', port=6379,db=0)
# Send a ping request and check the response 
print("Response:", redis_client.ping())


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_secure_string_customer():
    with open('cached_keys.txt', 'r') as file:
        lines = file.readlines()
    for line in lines:
        if "customer" in line:
            return line.strip()  # Return the line without leading/trailing whitespace
    return None


times = [f"{hour:02}:{minute:02}" for hour in range(24) for minute in (0, 30)]

@router.post("/Add_booking", tags=["Booking"])
async def add_booking( book_date_dropdown: booking_schema.BookingDates, book: booking_schema.BookingSchema, db:Session=Depends(get_db),  time : str = Query(..., description="Select a time", enum=times),current_user : User = Depends(get_current_user) ):
    # Combine date and time
    combined_datetime_str = f"{str(book_date_dropdown).split(',', 1)[1]} {str(time)}" 
    #customer_id = redis_client.get(get_secure_string_customer()).decode('utf-8')
    # Parse the combined string into a datetime object
    timedate = dtme.strptime(combined_datetime_str,"%Y-%m-%d %H:%M")
    responce = booking_mdl.add_booking(db=db, book=book, timedate=timedate,  user_id_request=current_user.id)
    return responce

@router.get("/Get_booking", tags=["Booking"])
async def get_booking_by_user(db:Session= Depends(get_db), current_user : User = Depends(get_current_user)):
    responce = booking_mdl.get_all_booking_by_user(db=db, user_id=current_user.id)
    return responce