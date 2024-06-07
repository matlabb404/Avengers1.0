from app.models import booking_model, api_test_model
from sqlalchemy.orm import Session
import json
from app.schemas import booking_schema
from app.config.db.postgresql import SessionLocal
from app.models.booking_model import Booking
from app.models.service_model import Service
from app.models.service_model import Add_Service
from app.models.vendor_model import Vendor
from sqlalchemy.dialects import postgresql
from uuid import UUID
from datetime import datetime




def add_booking(db:Session, book:booking_schema.BookingSchema, timedate: datetime, user_id_request: str ):
    db_booking = booking_model.Booking(time_date = timedate, service_id = book.service_id, user_id = user_id_request, notes = book.notes)
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


def get_all_booking_by_user(db:Session, user_id: int):
    db_query = db.query(Booking.service_id, Booking.notes, Booking.time_date).filter(Booking.user_id == user_id).all()

    booking_information_list = []

    for booking in db_query:

        #service query
        service_model_query = db.query(Service).filter(Service.id == booking.service_id).first()
        if not service_model_query:
            continue

        #add_Service query 
        service_name_query = db.query(Add_Service.service_name).filter(Add_Service.id == service_model_query.add_service_id).first()
        if not service_model_query:
            continue

        #vendor name
        vendor_query  =db.query(Vendor.business_name).filter(Vendor.vendor_id == service_model_query.add_vendor_id).first()
        if not vendor_query:
            continue

        booking_information = {  
            "Business Name": vendor_query.business_name,
            "Service Name": service_name_query.service_name,
            "Service Price" : service_model_query.price,
            "Booking Date" : booking.time_date,
            "Booking Notes" : booking.notes,
        }
        
        booking_information_list.append(booking_information)

    return booking_information_list

def delete_booking(db:Session, user_id_request:str, booking_id_request : str):
    db_query = db.query(Booking).filter(Booking.booking_id == booking_id_request, Booking.user_id == user_id_request).first()
    print(db_query)
    if db_query:
        db.delete(db_query)
        db.commit()
        return "Booking deleted Successfully"
    else:
        return "Booking Not Found. Please Try Again"