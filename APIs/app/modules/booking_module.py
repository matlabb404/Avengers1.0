from app.models.notification_model import NotificationTarget, NotificationType
from app.utils.money import from_minor_units
from fastapi import HTTPException
from app.models import booking_model, vendor_model
from sqlalchemy.orm import Session
from app.schemas import booking_schema
from app.modules import notification_module as nm, big_services_module as service_mdl
from app.models.booking_model import Booking, BookingStatus
from app.models.service_model import Service, Add_Service, price_history
from app.models.vendor_model import Vendor
from uuid import UUID
from datetime import timezone, datetime, date, timedelta
from sqlalchemy.exc import IntegrityError
from typing import List
from app.models.payment_model import PaymentStatus
from app.models.payment_model import Payment                 # adjust import path if different


def add_booking(db: Session, book: booking_schema.BookingCreate, user_id_request: str):
    try:
        booking_time = book.booking_time.replace(second=0, microsecond=0)

        if booking_time.tzinfo is None:
            booking_time = booking_time.replace(tzinfo=timezone.utc)

        if booking_time < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Cannot book past time")

        service = db.query(Service).filter(Service.id == book.service_id).first()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # ✅ Read price_history via Service FK
        if not service.price_history:
            raise HTTPException(
                status_code=400, 
                detail="Service has no price configured. Vendor must set prices first."
            )
        
        ph = db.query(price_history).filter(
            price_history.id == service.price_history
        ).first()
        
        if not ph or ph.price_minor <= 0:
            raise HTTPException(
                status_code=400, 
                detail="Service has no valid booking fee. Vendor must set booking fee first."
            )
        
        # ✅ Fetch the Add_Service to get the canonical price
        add_service = db.query(Add_Service).filter(
            Add_Service.id == service.add_service_id
        ).first()
        if not add_service:
            raise HTTPException(status_code=404, detail="Service catalog entry not found")

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

        booking_time = booking_time.astimezone(timezone.utc)

        new_booking = Booking(
            time_date=booking_time,
            service_id=book.service_id,
            user_id=user_id_request,
            notes=book.notes,
            price_minor_at_booking=ph.price_minor,      
            currency_at_booking=ph.currency,             
            status=booking_model.BookingStatus.INIT,
            payment_status=PaymentStatus.PENDING,
        )

        db.add(new_booking)
        db.flush()

        # Notify the vendor owner that their service was booked (same transaction).
        owner_id = nm.service_owner_user_id(db, book.service_id)
        if owner_id is not None:
            nm.notify(
                db,
                recipient_user_id=owner_id,
                type=NotificationType.BOOKING_NEW,
                actor_user_id=user_id_request,
                actor_name=None,  # optional: resolve the customer's name if you have it
                target_type=NotificationTarget.BOOKING,
                target_id=str(new_booking.booking_id),
                preview="booked your service",
                vendor_id=service.add_vendor_id,   # for per-vendor mute checks
                commit=False,
            )

        db.commit()
        db.refresh(new_booking)

        return new_booking
    
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate booking")

def get_booking_detail(
    db: Session,
    booking_id_request: str,
    user_id_request: str | None = None,
    ignore_user: bool = False,
):
    query = db.query(Booking).filter(
        Booking.booking_id == booking_id_request
    )

    if not ignore_user:
        query = query.filter(
            Booking.user_id == user_id_request
        )

    booking = query.first()

    if booking is None:
        raise HTTPException(404, "Booking not found")
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Full service — reuses the same builder the feed/post endpoints use.
    service_full = service_mdl.get_service(db, booking.service_id)

    # Denormalized display names come from the already-fetched service.
    business_name = service_full.vendor.business_name
    service_name = service_full.add_service.service_name

    # Most recent payment reference for this booking, if any.
    payment_ref = (
        db.query(Payment.provider_reference)
        .filter(Payment.booking_id == booking.booking_id)
        .order_by(Payment.created_at.desc())
        .first()
    )
    reference = payment_ref[0] if payment_ref else None

    booking_out = {
        "booking_id": str(booking.booking_id),
        "service_id": booking.service_id,
        "user_id": booking.user_id,
        "business_name": business_name,
        "service_name": service_name,
        "price_minor_at_booking": booking.price_minor_at_booking,
        "currency_at_booking": booking.currency_at_booking.value,
        "time_date": booking.time_date,
        "notes": booking.notes or "",
        "status": booking.status.value if booking.status else None,
        "payment_status": booking.payment_status.value if booking.payment_status else None,
    }

    return {
        "booking": booking_out,
        "service": service_full,
        "payment_reference": reference,
    }

def get_all_booking_by_user(db: Session, user_id: int):
    results = (
        db.query(
            Booking.booking_id,
            Booking.service_id,                # ADD — for rebook
            Service.add_vendor_id,  
            Booking.time_date,
            Booking.notes,
            Booking.status,
            Service.price,
            Add_Service.service_name,
            Booking.price_minor_at_booking,    # ✅ snapshot
            Booking.currency_at_booking,       # ✅ snapshot
            Booking.payment_status,            # ✅ new
            Add_Service.service_name,
            Vendor.business_name
        )
        .join(Service, Booking.service_id == Service.id)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.time_date.desc()) 
        .all()
    )

    return [
        {
            "booking_id": str(r.booking_id),
            "service_id": str(r.service_id),           
            "vendor_id": str(r.add_vendor_id),
            "business_name": r.business_name,
            "service_name": r.service_name,
            "price": from_minor_units(r.price_minor_at_booking, r.currency_at_booking),
            "currency": r.currency_at_booking.value,
            "booking_date": r.time_date,
            "notes": r.notes,
            "status": r.status.value if r.status else None,
            "payment_status": r.payment_status.value if r.payment_status else None,
        }
        for r in results
    ]

def _vb_encode_cursor(dt, booking_id) -> str:
    """Opaque keyset cursor over (time_date, booking_id)."""
    import base64
    raw = f"{dt.isoformat()}|{booking_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _vb_decode_cursor(cursor: str):
    import base64
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts, bid = raw.split("|", 1)
    return datetime.fromisoformat(ts), bid


def _vb_relative(dt, now) -> str | None:
    """Compact human label: 'in 45m', 'in 3h', 'in 2d', '5h ago', '3d ago'."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    secs = (dt - now).total_seconds()
    future = secs >= 0
    secs = abs(secs)
    if secs < 3600:
        label = f"{max(1, int(secs // 60))}m"
    elif secs < 86400:
        label = f"{int(secs // 3600)}h"
    else:
        label = f"{int(secs // 86400)}d"
    return f"in {label}" if future else f"{label} ago"


def _vb_avatar_item(asset) -> dict | None:
    """MediaAsset -> the MediaItem shape the client already renders, or None."""
    if asset is None:
        return None
    derivatives = asset.derivatives or {}
    return {
        "asset_id": asset.id,
        "kind": asset.kind,
        "status": asset.status,
        "original_url": asset.original_url,
        "thumbnail_url": derivatives.get("thumbnail"),
        "width": asset.width,
        "height": asset.height,
    }


def get_vendor_bookings(
    db: Session,
    vendor_id: str,
    *,
    section: str = "upcoming",
    limit: int = 20,
    cursor: str | None = None,
) -> dict:
    """
    Bookings FOR this vendor's services, split into two sections and keyset-paginated.

      upcoming: CONFIRMED (paid) bookings whose time is still ahead, soonest first.
      past:     CONFIRMED-but-elapsed + COMPLETED bookings, most recent first.

    Expired holds and cancellations (CANCELLED) and unpaid transient holds
    (INIT/PENDING) are deliberately excluded from both — the vendor only sees real,
    paid bookings. Each row carries the customer (name/avatar/phone/email), the
    service, time + a relative label, duration, the price and the vendor's payout
    (price minus the platform commission), and payment/booking status + notes.
    """
    from sqlalchemy import and_, or_
    from app.models.customer_model import customer as CustomerModel
    from app.models.account_model import User
    from app.models.media_model import MediaAsset
    from app.config.settings import get_settings

    section = (section or "upcoming").lower()
    if section not in ("upcoming", "past"):
        raise HTTPException(400, "section must be 'upcoming' or 'past'")
    limit = max(1, min(limit, 50))
    now = datetime.utcnow()  # naive UTC, matches the stored (naive) time_date column

    q = (
        db.query(Booking, Add_Service, Vendor, CustomerModel, User, MediaAsset)
        .join(Service, Booking.service_id == Service.id)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .outerjoin(CustomerModel, CustomerModel.user_id == Booking.user_id)
        .outerjoin(User, User.id == Booking.user_id)
        .outerjoin(MediaAsset, MediaAsset.id == CustomerModel.avatar_asset_id)
        .filter(Service.add_vendor_id == vendor_id)
    )

    if section == "upcoming":
        q = q.filter(
            Booking.status == BookingStatus.CONFIRMED,
            Booking.time_date >= now,
        )
        if cursor:
            c_ts, c_id = _vb_decode_cursor(cursor)
            q = q.filter(
                or_(
                    Booking.time_date > c_ts,
                    and_(Booking.time_date == c_ts, Booking.booking_id > c_id),
                )
            )
        q = q.order_by(Booking.time_date.asc(), Booking.booking_id.asc())
    else:  # past
        q = q.filter(
            or_(
                and_(Booking.status == BookingStatus.CONFIRMED, Booking.time_date < now),
                Booking.status == BookingStatus.COMPLETED,
            )
        )
        if cursor:
            c_ts, c_id = _vb_decode_cursor(cursor)
            q = q.filter(
                or_(
                    Booking.time_date < c_ts,
                    and_(Booking.time_date == c_ts, Booking.booking_id < c_id),
                )
            )
        q = q.order_by(Booking.time_date.desc(), Booking.booking_id.desc())

    rows = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    fee_pct = get_settings().PLATFORM_FEE_PERCENTAGE

    items = []
    for booking, add_service, vendor, cust, user, asset in rows:
        price_minor = booking.price_minor_at_booking or 0
        payout_minor = round(price_minor * (100 - fee_pct) / 100)
        currency = booking.currency_at_booking
        items.append({
            "booking_id": str(booking.booking_id),
            "service_id": str(booking.service_id),
            "vendor_id": str(vendor.vendor_id),
            "customer_name": (cust.name if cust and cust.name else "Customer"),
            "customer_avatar": _vb_avatar_item(asset),
            "customer_phone": (cust.phone if cust else None),
            "customer_email": (user.email if user else None),
            "business_name": vendor.business_name,
            "service_name": add_service.service_name,
            "booking_date": booking.time_date,
            "when_relative": _vb_relative(booking.time_date, now),
            "duration_minutes": add_service.interval_minutes,
            "price": from_minor_units(price_minor, currency),
            "payout": from_minor_units(payout_minor, currency),
            "currency": currency.value,
            "notes": booking.notes,
            "status": booking.status.value if booking.status else None,
            "payment_status": booking.payment_status.value if booking.payment_status else None,
        })

    next_cursor = None
    if has_more and rows:
        last_booking = rows[-1][0]
        next_cursor = _vb_encode_cursor(last_booking.time_date, last_booking.booking_id)

    return {"section": section, "items": items, "next_cursor": next_cursor}

def cancel_booking(db:Session, user_id_request:str, booking_id_request : str):
    db_query = db.query(Booking).filter(
        Booking.booking_id == booking_id_request,
        Booking.user_id == user_id_request,
        Booking.status.in_([BookingStatus.INIT, BookingStatus.CONFIRMED])
    ).first()

    if not db_query:
        return {"ok": False, "message": "Booking not found or cannot be cancelled"}

    slot = db.query(booking_model.Slot).filter(
        booking_model.Slot.service_id == db_query.service_id,
        booking_model.Slot.time == db_query.time_date
    ).with_for_update().first()

    if slot:
        slot.booked = max(slot.booked - 1, 0)

    db_query.status = BookingStatus.CANCELLED

    # Resolve the vendor owner for this booking's service.
    owner_id = nm.service_owner_user_id(db, db_query.service_id)
    # We also need the vendor_id for mute checks.
    from app.models.service_model import Service as _Service
    svc = db.query(_Service.add_vendor_id).filter(_Service.id == db_query.service_id).first()
    vendor_id = svc[0] if svc else None

    # Notify the vendor: a booking was cancelled by the customer.
    if owner_id is not None:
        nm.notify(
            db,
            recipient_user_id=owner_id,
            type=NotificationType.BOOKING_CANCELLED,
            actor_user_id=user_id_request,
            actor_name=None,
            target_type=NotificationTarget.BOOKING,
            target_id=str(db_query.booking_id),
            preview="cancelled their booking",
            vendor_id=vendor_id,
            commit=False,
        )

    # Confirm to the customer that THEIR cancellation went through.
    nm.notify(
        db,
        recipient_user_id=db_query.user_id,
        type=NotificationType.BOOKING_CANCELLED,
        actor_user_id=None,                 # system/self confirmation
        actor_name=None,
        target_type=NotificationTarget.BOOKING,
        target_id=str(db_query.booking_id),
        preview="Your booking was cancelled",
        vendor_id=vendor_id,
        commit=False,
    )

    db.commit()
    return {"ok": True, "message": "Booking cancelled successfully"}

def get_service_availability(db: Session, service_id: UUID, selected_date: date): #To get timeslots for that day, have to 

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

    start_datetime = datetime.combine(selected_date, start_time).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(selected_date, end_time).replace(tzinfo=timezone.utc)

    slots = db.query(booking_model.Slot).filter(
        booking_model.Slot.service_id == service_id,
        booking_model.Slot.time >= start_datetime,
        booking_model.Slot.time < end_datetime
    ).all()

    slot_map = {
        slot.time.replace(tzinfo=timezone.utc): slot
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

        current += timedelta(minutes=interval)

    return result

def get_service_availability_range(
    db: Session,
    service_id: UUID,
    start_date: date,
    end_date: date
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

        current_date += timedelta(days=1)

    return result

def get_service_unavailability(
    db: Session,
    service_id: UUID,
    start_date: date,
    end_date: date
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
            current_date += timedelta(days=1)
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
            current_date += timedelta(days=1)
            continue

        # Determine working hours
        start_time = exception.start_time if exception and exception.start_time else schedule.start_time
        end_time = exception.end_time if exception and exception.end_time else schedule.end_time
        capacity = exception.capacity if exception and exception.capacity else schedule.capacity
        interval = add_serv.interval_minutes

        start_dt = datetime.combine(current_date, start_time).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(current_date, end_time).replace(tzinfo=timezone.utc)

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

            current_time += timedelta(minutes=interval)

        if all_full:
            result.append({
                "date": current_date,
                "reason": "fully_booked"
            })

        current_date += timedelta(days=1)

    return result

def generate_slots(
    schedule: vendor_model.Scheduling_,
    exceptions: List[vendor_model.ScheduleException],
    start_date: date,
    end_date: date
):
    results = []
    current = start_date

    exception_map = {e.date: e for e in exceptions}

    while current <= end_date:
        weekday = current.strftime("%A").lower()

        if weekday not in schedule.days:
            current += timedelta(days=1)
            continue

        exception = exception_map.get(current)

        if exception and exception.is_closed:
            current += timedelta(days=1)
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
            slot_end = current_dt + timedelta(minutes=schedule.interval_minutes)

            results.append({
                "start": current_dt,
                "end": slot_end,
                "capacity": capacity
            })

            current_dt = slot_end

        current += timedelta(days=1)

    return results