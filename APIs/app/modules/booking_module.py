from app.models import booking_model, api_test_model
from sqlalchemy.orm import Session
import json
from app.schemas import booking_schema
from app.config.db.postgresql import SessionLocal
from app.models.booking_model import Booking
from sqlalchemy.dialects import postgresql
from uuid import UUID
from datetime import datetime




def add_booking(db:Session, book:booking_schema.BookingSchema, timedate: datetime, user_id_request: str ):
    db_booking = booking_model.Booking(time_date = timedate, service_id = book.service_id, user_id = user_id_request, notes = book.notes)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking