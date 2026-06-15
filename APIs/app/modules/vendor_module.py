from operator import and_, or_
from warnings import deprecated

from app.config.settings import get_settings
from app.models import vendor_model
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, List
from app.models.account_model import User
from app.schemas import vendor_Schema
from app.modules import social_module
from app.models.vendor_model import Vendor
from uuid import UUID
from fastapi import HTTPException



def add_vendor(db:Session, vendor:vendor_Schema.VendorCreateBase, vendor_emaail : str, user_id_ :str ):
    db_vendor = vendor_model.Vendor(**vendor.dict(), vendor_email = vendor_emaail, user_id = user_id_)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    user = db.query(User).filter(User.id == user_id_).first()
    if not user:
        email = None  # fallback if no matching user found
    else:
        email = user.email
    return {
        "vendor": db_vendor,
        "user_email": email
    }

def vendor_update(db:Session, vendor_id: UUID, vendor_update:vendor_Schema.VendorCreateBase):
    db_vendor = db.query(vendor_model.Vendor).filter(vendor_model.Vendor.vendor_id == vendor_id).first()
    if db_vendor:
        for key, value in vendor_update.dict().items():  
            setattr(db_vendor, key, value)
        db.commit()
        db.refresh(db_vendor)
        return db_vendor
    else:
        return 'Not_Found'
    
def vendor_delete(db:Session, vendor_id: UUID):
    db_vendor = db.query(vendor_model.Vendor).filter(vendor_model.Vendor.vendor_id == vendor_id).first()
    if db_vendor:
        db.delete(db_vendor)
        db.commit()
        return True
    else:
        return False
    
def vendor_details_delete(db:Session, vendor_id_details: UUID):
    db_vendor = db.query(vendor_model.Vendor_Details).filter(vendor_model.Vendor_Details.id == vendor_id_details).first()
    if db_vendor:
        db.delete(db_vendor)
        db.commit()
        return True
    else:
        return False

def add_vendor_details(db:Session, vendor_id: UUID ,vendor_details_request:vendor_Schema.VendorDetailsCreateBase):
    db_vendor_details = vendor_model.Vendor_Details(vendor_id_details=vendor_id,
                                       description=vendor_details_request.description,
                                       picture_url=vendor_details_request.picture_url,
                                       review=vendor_details_request.review)
    db.add(db_vendor_details)
    db.commit()
    db.refresh(db_vendor_details)
    return db_vendor_details

def get_all_vendors(db:Session):
    all_vendors = db.query(Vendor).all()
    return all_vendors

def get_gender_vendors(gender, db:Session):
    all_vendors = db.query(Vendor).filter(Vendor.gender == gender).all()
    return all_vendors

### FOR SCHEDULING NOW
def __schedule(db:Session, schedule_vendor_id: UUID, schedulebase:vendor_Schema.Scheduling):
    scheduling = vendor_model.Scheduling_(schedule_vendor_id = schedule_vendor_id,
                                       days = schedulebase.days,
                                       exceptions = schedulebase.exceptions,
                                       service_id = schedulebase.service_id
                                       )
    db.add(scheduling)
    db.commit()
    db.refresh(scheduling)
    return scheduling


def get_current_vendor(user_id: str, db: Session ):
    vendor = db.query(vendor_model.Vendor).filter(vendor_model.Vendor.user_id == user_id).first()
    return vendor

@deprecated(reason="Use get_vendor_public_profile instead, which includes follower_count and rating info.")
def get_vendor_public_profile(db: Session, user, vendor_id):
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return {
        "vendor_id": vendor.vendor_id,
        "first_name": vendor.first_name,
        "last_name": vendor.last_name,
        "business_name": vendor.business_name,
        "city": vendor.city,
        "country": vendor.country,
        "follower_count": social_module.follower_count(db, vendor_id),
        "is_following": social_module.is_following(db, user, vendor_id),
    }

# ═════════════════════════════════════════════════════════════════════════════
# VENDOR PROFILE  (public profile of another vendor + their posts)
# ═════════════════════════════════════════════════════════════════════════════
#
# get_vendor_profile: header data (name/business/location) + global follower_count
#   + per-user is_following. Per-user field => router marks it private/no-store.
#
# get_vendor_services: the distinct services this vendor offers, to build the
#   filter chips on the profile (id + name).
#
# get_vendor_posts: this vendor's posts, newest-first, keyset-paginated, optionally
#   filtered to a single service (by add_service.id). Same FeedPage shape as
#   Discover/Following so the client reuses FeedList.


def get_vendor_profile(db: Session, user: User, vendor_id: UUID) -> dict:
    """
    Public profile of a vendor as seen by the current user.
    Returns the VendorPublicProfile shape.
    """
    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")

    # Average rating across all this vendor's posts (sum of rating_sum / sum of
    # rating_count over their services). Done in one aggregate query.
    from app.models.service_model import Service
    from sqlalchemy import func as _func

    agg = (
        db.query(
            _func.coalesce(_func.sum(Service.rating_sum), 0),
            _func.coalesce(_func.sum(Service.rating_count), 0),
        )
        .filter(Service.add_vendor_id == vendor_id)
        .first()
    )
    total_sum, total_count = (agg[0] or 0), (agg[1] or 0)
    rating_avg = round(total_sum / total_count, 2) if total_count > 0 else None

    return {
        "vendor_id": vendor.vendor_id,
        "first_name": vendor.first_name,
        "last_name": vendor.last_name,
        "business_name": vendor.business_name,
        "city": vendor.city,
        "country": vendor.country,
        "follower_count": social_module.follower_count(db, vendor_id),
        "is_following": social_module.is_following(db, user, vendor_id),
        "rating_avg": rating_avg,
        "rating_count": total_count,
    }


def get_vendor_services(db: Session, vendor_id: UUID) -> list[dict]:
    """
    Distinct services this vendor has posted, for the profile's filter chips.
    Returns [{id, name}], deduplicated, ordered by name.
    """
    from app.models.service_model import Service, Add_Service

    rows = (
        db.query(Add_Service.id, Add_Service.service_name)
        .join(Service, Service.add_service_id == Add_Service.id)
        .filter(Service.add_vendor_id == vendor_id)
        .distinct()
        .all()
    )
    seen = []
    out = []
    for sid, name in rows:
        if sid in seen:
            continue
        seen.append(sid)
        out.append({"id": sid, "name": name})
    out.sort(key=lambda x: (x["name"] or "").lower())
    return out


def get_vendor_posts(
    db: Session,
    vendor_id: UUID,
    service: Optional[str] = None,
    limit: int = 20,
    cursor: Optional[str] = None,
) -> dict:
    """
    A vendor's posts, newest-first, keyset-paginated. Optionally filtered to a
    single service by add_service.id (the `service` query param). FeedPage shape.
    """
    from app.models.service_model import Service, Add_Service, price_history
    from app.modules.big_services_module import _build_full_response

    vendor = db.query(Vendor).filter(Vendor.vendor_id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")

    limit = max(1, min(limit, 50))

    q = (
        db.query(Service, Vendor, price_history, Add_Service)
        .join(Add_Service, Service.add_service_id == Add_Service.id)
        .join(Vendor, Service.add_vendor_id == Vendor.vendor_id)
        .join(price_history, Service.price_history == price_history.id)
        .filter(Service.add_vendor_id == vendor_id)
    )

    # Optional service filter (add_service.id is a VARCHAR PK, compared as string).
    if service and service.strip().lower() not in ("", "all"):
        q = q.filter(Service.add_service_id == service.strip())

    if cursor:
        c_ts, c_id = social_module._decode_cursor(cursor)
        q = q.filter(
            or_(
                Service.created_at < c_ts,
                and_(Service.created_at == c_ts, Service.id < c_id),
            )
        )

    q = q.order_by(Service.created_at.desc(), Service.id.desc()).limit(limit + 1)
    rows = q.all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for svc, vnd, ph, add_service in rows:
        post = _build_full_response(db, svc, vnd, ph, add_service)
        items.append({"post": post, "counts": social_module._counts_for(svc)})

    next_cursor = None
    if has_more and rows:
        last_service = rows[-1][0]
        next_cursor = social_module._encode_cursor(last_service.created_at, last_service.id)

    return {"items": items, "next_cursor": next_cursor}

# ============ SCHEDULE CRUD ============

def get_schedule_for_service(
    db: Session,
    vendor_id: str,
    service_id: str = "all"
) -> Optional[vendor_model.Scheduling_]:
    """
    Get schedule with proper hierarchy:
    1. Try service-specific schedule first
    2. Fall back to "all" schedule if not found
    """
    # Try service-specific first
    if service_id != "all":
        specific = db.query(vendor_model.Scheduling_).filter(
            vendor_model.Scheduling_.schedule_vendor_id == vendor_id,
            vendor_model.Scheduling_.service_id == service_id
        ).first()
        
        if specific:
            return specific
    
    # Fall back to "all"
    return db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == vendor_id,
        vendor_model.Scheduling_.service_id == "all"
    ).first()

def upsert_schedule(
    db: Session,
    vendor_id: str,
    schedule_data: vendor_Schema.ScheduleCreate
) -> vendor_model.Scheduling_:
    """
    Create or update schedule (UPSERT pattern)
    """
    existing = db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == vendor_id,
        vendor_model.Scheduling_.service_id == schedule_data.service_id
    ).first()
    
    if existing:
        # UPDATE
        for key, value in schedule_data.dict(exclude_unset=True).items():
            setattr(existing, key, value)
        schedule = existing
    else:
        # CREATE
        schedule = vendor_model.Scheduling_(
            schedule_vendor_id=vendor_id,
            **schedule_data.dict()
        )
        db.add(schedule)
    
    db.commit()
    db.refresh(schedule)
    return schedule

def update_schedule(
    db: Session,
    vendor_id: str,
    service_id: str,
    update_data: vendor_Schema.ScheduleUpdate
) -> vendor_model.Scheduling_:
    """
    Update existing schedule (partial update)
    """
    schedule = db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == vendor_id,
        vendor_model.Scheduling_.service_id == service_id
    ).first()
    
    if not schedule:
        raise HTTPException(
            status_code=404,
            detail=f"No schedule found for service_id: {service_id}"
        )
    
    # Update only provided fields
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    return schedule

def delete_schedule(
    db: Session,
    vendor_id: str,
    service_id: str
) -> dict:
    """
    Delete schedule (to revert to default "all" schedule)
    """
    if service_id == "all":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default 'all' schedule. Update it instead."
        )
    
    schedule = db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == vendor_id,
        vendor_model.Scheduling_.service_id == service_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {"status": "deleted", "message": "Reverted to default schedule"}

def get_all_schedules(
    db: Session,
    vendor_id: str
) -> List[vendor_model.Scheduling_]:
    """
    Get all schedules for a vendor (including service-specific ones)
    """
    return db.query(vendor_model.Scheduling_).filter(
        vendor_model.Scheduling_.schedule_vendor_id == vendor_id
    ).all()

# ============ EXCEPTION CRUD ============

def get_exceptions_for_service(
    db: Session,
    vendor_id: str,
    start_date: date,
    end_date: date,
    service_id: str = "all"
) -> List[vendor_model.ScheduleException]:
    """
    Get exceptions with proper hierarchy:
    1. Service-specific exceptions
    2. "all" exceptions
    """
    # Get both service-specific and "all" exceptions
    exceptions = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.vendor_id == vendor_id,
        vendor_model.ScheduleException.date >= start_date,
        vendor_model.ScheduleException.date <= end_date,
        vendor_model.ScheduleException.service_id.in_([service_id, "all"])
    ).all()
    
    # If we have service-specific exception for a date, it overrides "all"
    exception_map = {}
    
    for exc in exceptions:
        key = exc.date
        
        # Service-specific takes precedence
        if exc.service_id == service_id:
            exception_map[key] = exc
        elif key not in exception_map:
            exception_map[key] = exc
    
    return list(exception_map.values())

def create_exception(
    db: Session,
    vendor_id: str,
    exception_data: vendor_Schema.ExceptionCreate
) -> vendor_model.ScheduleException:
    """
    Create schedule exception
    """
    # Check if exception already exists
    existing = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.vendor_id == vendor_id,
        vendor_model.ScheduleException.service_id == exception_data.service_id,
        vendor_model.ScheduleException.date == exception_data.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Exception already exists for this date and service"
        )
    
    exception = vendor_model.ScheduleException(
        vendor_id=vendor_id,
        **exception_data.dict()
    )
    
    db.add(exception)
    db.commit()
    db.refresh(exception)
    return exception

def update_exception(
    db: Session,
    exception_id: str,
    update_data: vendor_Schema.ExceptionBase
) -> vendor_model.ScheduleException:
    """
    Update existing exception
    """
    exception = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(exception, key, value)
    
    db.commit()
    db.refresh(exception)
    return exception

def delete_exception(
    db: Session,
    exception_id: str
) -> dict:
    """
    Delete exception
    """
    exception = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.id == exception_id
    ).first()
    
    if not exception:
        raise HTTPException(status_code=404, detail="Exception not found")
    
    db.delete(exception)
    db.commit()
    
    return {"status": "deleted"}

def cleanup_past_exceptions(db: Session, vendor_id: Optional[str] = None):
    """
    Delete exceptions that are in the past
    Can be called:
    1. As a background task (cron)
    2. Before querying exceptions
    3. Manually via API endpoint
    """
    from datetime import date
    
    query = db.query(vendor_model.ScheduleException).filter(
        vendor_model.ScheduleException.date < date.today()
    )
    
    if vendor_id:
        query = query.filter(vendor_model.ScheduleException.vendor_id == vendor_id)
    
    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    
    return {"deleted_count": deleted_count}

# ============ AVAILABILITY GENERATION ============

def generate_availability(
    db: Session,
    vendor_id: str,
    service_id: str,
    start_date: date,
    end_date: date
) -> List[dict]:
    """
    Generate availability slots considering:
    1. Service-specific schedule OR "all" schedule
    2. Service-specific exceptions + "all" exceptions
    """
    # Cleanup old exceptions first
    cleanup_past_exceptions(db, vendor_id)
    
    # Get schedule (with hierarchy)
    schedule = get_schedule_for_service(db, vendor_id, service_id)
    
    if not schedule:
        return []
    
    # Get exceptions (with hierarchy)
    exceptions = get_exceptions_for_service(
        db, vendor_id, start_date, end_date, service_id
    )
    
    # Build exception map
    exception_map = {exc.date: exc for exc in exceptions}
    
    # Generate slots
    slots = []
    current_date = start_date
    
    while current_date <= end_date:
        weekday = current_date.strftime("%a").lower()
        
        # Check if this day is in working days
        if weekday not in [d.lower() for d in schedule.days]:
            current_date += timedelta(days=1)
            continue
        
        # Check for exception
        exception = exception_map.get(current_date)
        
        if exception and exception.is_closed:
            # Day is closed
            current_date += timedelta(days=1)
            continue
        
        # Determine times and capacity
        if exception:
            start_time = exception.start_time or schedule.start_time
            end_time = exception.end_time or schedule.end_time
            capacity = exception.capacity or schedule.capacity
            walk_in = exception.walk_in_available if exception.walk_in_available is not None else schedule.walk_in_available
        else:
            start_time = schedule.start_time
            end_time = schedule.end_time
            capacity = schedule.capacity
            walk_in = schedule.walk_in_available
        
        # Generate time slots for this day
        from datetime import datetime, timedelta as td
        
        current_time = datetime.combine(current_date, start_time)
        end_datetime = datetime.combine(current_date, end_time)
        
        while current_time < end_datetime:
            slot_end = current_time + td(minutes=schedule.interval_minutes)
            
            slots.append({
                "date": current_date.isoformat(),
                "start_time": current_time.time().strftime("%H:%M"),
                "end_time": slot_end.time().strftime("%H:%M"),
                "capacity": capacity,
                "walk_in_available": walk_in
            })
            
            current_time = slot_end
        
        current_date += timedelta(days=1)
    
    return slots