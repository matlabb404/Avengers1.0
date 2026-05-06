from fastapi import HTTPException
from app.models import booking_model, vendor_model
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
import datetime
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from collections import Counter
from typing import List

def add_booking(db: Session, book: booking_schema.BookingCreate, user_id_request: str):
    try:
        booking_time = book.booking_time.replace(second=0, microsecond=0)

        if booking_time.tzinfo is None:
            booking_time = booking_time.replace(tzinfo=datetime.timezone.utc)

        if booking_time < datetime.now(datetime.timezone.utc):
            raise HTTPException(status_code=400, detail="Cannot book past time")

        service = db.query(Service).filter(Service.id == book.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        schedule = db.query(vendor_model.Scheduling_).filter(
            vendor_model.Scheduling_.schedule_vendor_id == service.add_vendor_id
        ).first()

        if not schedule:
            raise HTTPException(status_code=400, detail="No schedule configured")

        # 🔒 LOCK rows involved in this slot
        slot = (
            db.query(booking_model.Slot)
            .filter(
                booking_model.Slot.service_id == book.service_id,
                booking_model.Slot.time == booking_time
            )
            .with_for_update()
            .first()
        )

        if not slot:
            slot = booking_model.Slot(
                service_id=book.service_id,
                time=booking_time,
                capacity=schedule.capacity,
                booked=0
            )
            db.add(slot)
            db.flush()

        if slot.booked >= slot.capacity:
            raise HTTPException(status_code=400, detail="Slot fully booked")

        slot.booked += 1

        booking_time = booking_time.astimezone(datetime.timezone.utc)

        new_booking = Booking(
            time_date=booking_time,
            service_id=book.service_id,
            user_id=user_id_request,
            notes=book.notes
        )

        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)

        return new_booking
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate booking")

def get_all_booking_by_user(db: Session, user_id: int):
    results = (
        db.query(
            Booking.time_date,
            Booking.notes,
            Service.price,
            Add_Service.service_name,
            Vendor.business_name
        )
        .join(Service, Booking.service_id == Service.id)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .filter(Booking.user_id == user_id)
        .all()
    )

    return [
        {
            "business_name": r.business_name,
            "service_name": r.service_name,
            "price": r.price,
            "booking_date": r.time_date,
            "notes": r.notes,
        }
        for r in results
    ]

def cancel_booking(db:Session, user_id_request:str, booking_id_request : str):
    db_query = db.query(Booking).filter(
        Booking.booking_id == booking_id_request,
        Booking.user_id == user_id_request,
        Booking.status == "pending"
    ).first()

    if not db_query:
        return "Booking Not Found. Please Try Again"

    slot = db.query(booking_model.Slot).filter(
        booking_model.Slot.service_id == db_query.service_id,
        booking_model.Slot.time == db_query.time_date
    ).with_for_update().first()

    if slot:
        slot.booked = max(slot.booked - 1, 0)

    db_query.status = "cancelled"
    db.commit()
    return "Booking deleted Successfully"

def get_service_availability(db: Session, service_id: UUID, selected_date: datetime.date): #To get timeslots for that day, have to 

    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    add_serv = db.query(Add_Service).filter(Add_Service.id == service.add_service_id).first()

    schedule = db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == service.add_vendor_id, vendor_model.Scheduling_.service_id == add_serv.id
    ).first()
    if not schedule:
        return []

    interval = add_serv.interval_minutes

    weekday = selected_date.strftime("%a").lower()
    if weekday not in [d.lower() for d in schedule.days]:
        return []

    exception = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.vendor_id == service.add_vendor_id,
        vendor_model.ScheduleException.date == selected_date,
        vendor_model.ScheduleException.service_id == add_serv.id
    ).first()

    if exception:
        if exception.is_closed:
            return []

        start_time = exception.start_time or schedule.start_time
        end_time = exception.end_time or schedule.end_time
        capacity = exception.capacity or schedule.capacity
    else:
        start_time = schedule.start_time
        end_time = schedule.end_time
        capacity = schedule.capacity

    start_datetime = datetime.datetime.combine(selected_date, start_time).replace(tzinfo=datetime.timezone.utc)
    end_datetime = datetime.datetime.combine(selected_date, end_time).replace(tzinfo=datetime.timezone.utc)

    slots = db.query(booking_model.Slot).filter(
        booking_model.Slot.service_id == service_id,
        booking_model.Slot.time >= start_datetime,
        booking_model.Slot.time < end_datetime
    ).all()

    slot_map = {
        slot.time.replace(tzinfo=datetime.timezone.utc): slot
        for slot in slots
    }

    current = start_datetime
    result = []

    while current < end_datetime:
        slot = slot_map.get(current)

        if slot:
            available = slot.capacity - slot.booked
        else:
            available = capacity

        result.append({
            "time": current.strftime("%H:%M"),
            "available_slots": max(available, 0),
            "is_available": available > 0
        })

        current += datetime.timedelta(minutes=interval)

    return result

def get_service_availability_range(
    db: Session,
    service_id: UUID,
    start_date: datetime.date,
    end_date: datetime.date
):
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="Invalid date range")

    days = (end_date - start_date).days + 1

    # guardrail (avoid abuse)
    if days > 30:
        raise HTTPException(status_code=400, detail="Range too large (max 30 days)")

    result = []

    current_date = start_date

    while current_date <= end_date:
        daily_slots = get_service_availability(db, service_id, current_date)

        result.append({
            "date": current_date.isoformat(),
            "slots": daily_slots
        })

        current_date += datetime.timedelta(days=1)

    return result

def get_service_unavailability(
    db: Session,
    service_id: UUID,
    start_date: datetime.date,
    end_date: datetime.date
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
        
    add_serv = db.query(Add_Service).filter(Add_Service.id == service.add_service_id).first()

    schedule = db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == service.add_vendor_id,
        vendor_model.Scheduling_.service_id == add_serv.id
    ).first()

    if not schedule:
        return []

    result = []

    current_date = start_date

    while current_date <= end_date:

        weekday = current_date.strftime("%a").lower()

        # ❌ Not in working days
        if weekday not in [d.lower() for d in schedule.days]:
            result.append({
                "date": current_date,
                "reason": "not_working_day"
            })
            current_date += datetime.timedelta(days=1)
            continue

        # 🔍 Check exception
        exception = db.query(vendor_model.ScheduleException).filter(
            vendor_model.ScheduleException.vendor_id == service.add_vendor_id,
            vendor_model.ScheduleException.date == current_date,
            vendor_model.ScheduleException.service_id == add_serv.id
        ).first()

        if exception and exception.is_closed:
            result.append({
                "date": current_date,
                "reason": "closed_exception"
            })
            current_date += datetime.timedelta(days=1)
            continue

        # Determine working hours
        start_time = exception.start_time if exception and exception.start_time else schedule.start_time
        end_time = exception.end_time if exception and exception.end_time else schedule.end_time
        capacity = exception.capacity if exception and exception.capacity else schedule.capacity
        interval = add_serv.interval_minutes

        start_dt = datetime.datetime.combine(current_date, start_time).replace(tzinfo=datetime.timezone.utc)
        end_dt = datetime.datetime.combine(current_date, end_time).replace(tzinfo=datetime.timezone.utc)

        # Get slots
        slots = db.query(booking_model.Slot).filter(
            booking_model.Slot.service_id == service_id,
            booking_model.Slot.time >= start_dt,
            booking_model.Slot.time < end_dt
        ).all()

        slot_map = {slot.time: slot for slot in slots}

        current_time = start_dt
        all_full = True

        while current_time < end_dt:
            slot = slot_map.get(current_time)

            if slot:
                available = slot.capacity - slot.booked
            else:
                # slot not created → still available
                available = capacity

            if available > 0:
                all_full = False
                break

            current_time += datetime.timedelta(minutes=interval)

        if all_full:
            result.append({
                "date": current_date,
                "reason": "fully_booked"
            })

        current_date += datetime.timedelta(days=1)

    return result

def generate_slots(
    schedule: vendor_model.Scheduling_,
    exceptions: List[vendor_model.ScheduleException],
    start_date: datetime.date,
    end_date: datetime.date
):
    results = []
    current = start_date

    exception_map = {e.date: e for e in exceptions}

    while current <= end_date:
        weekday = current.strftime("%A").lower()

        if weekday not in schedule.days:
            current += datetime.timedelta(days=1)
            continue

        exception = exception_map.get(current)

        if exception and exception.is_closed:
            current += datetime.timedelta(days=1)
            continue

        start_time = schedule.start_time
        end_time = schedule.end_time
        capacity = schedule.capacity

        if exception:
            if exception.start_time:
                start_time = exception.start_time
            if exception.end_time:
                end_time = exception.end_time
            if exception.capacity:
                capacity = exception.capacity

        current_dt = datetime.combine(current, start_time)
        end_dt = datetime.combine(current, end_time)

        while current_dt < end_dt:
            slot_end = current_dt + datetime.timedelta(minutes=schedule.interval_minutes)

            results.append({
                "start": current_dt,
                "end": slot_end,
                "capacity": capacity
            })

            current_dt = slot_end

        current += datetime.timedelta(days=1)

    return results