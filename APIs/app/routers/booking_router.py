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
import hashlib,secrets,string

router = APIRouter(prefix="/Booking")


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

@router.post("/add_booking", tags=["Booking"])
async def add_booking(
    book: booking_schema.BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return booking_mdl.add_booking(
        db=db,
        book=book,
        user_id_request=current_user.id
    )

@router.get("/get_booking", tags=["Booking"])
async def get_booking_by_user(db:Session= Depends(get_db), current_user : User = Depends(get_current_user)):
    responce = booking_mdl.get_all_booking_by_user(db=db, user_id=current_user.id)
    return responce


@router.delete("/delete_booking/{booking_id}", tags=["Booking"])
async def delete_booking_by_user(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return booking_mdl.cancel_booking(
        db=db,
        booking_id_request=booking_id,
        user_id_request=current_user.id
    )

@router.get("/availability", tags=["Booking"])
def get_availability(
    service_id: UUID,
    date: datetime.date,
    db: Session = Depends(get_db)
):
    return booking_mdl.get_service_availability(db, service_id, date)

@router.get("/unavailability", tags=["Booking"])
def get_unavailability(
    service_id: UUID,
    start_date: datetime.date,
    end_date: datetime.date,
    db: Session = Depends(get_db)
):
    return booking_mdl.get_service_unavailability(
        db, service_id, start_date, end_date
    )