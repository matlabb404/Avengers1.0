from datetime import datetime, timezone
from app.models.payment_model import Currency
from app.schemas.services_schema import SetServicePriceRequest
from sqlalchemy.orm import Session
from app.models.service_model import Add_Service, price_history
from app.utils.money import to_minor_units
from fastapi import HTTPException


def add_s(db:Session, strid:str ,service: str, interval_minutes:int, vendor_id:str):
    db_service = Add_Service(id=strid,service_name=service, interval_minutes=interval_minutes, vendor_id=vendor_id)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return {"Service Added Successfully" :db_service}

def update_s(db:Session, strid:str, service:str, interval_minutes:int, vendor_id: str):
    db_service = db.query(Add_Service).filter(Add_Service.id == strid, Add_Service.vendor_id == str(vendor_id) ).first()
    if db_service:
        db_service.service_name = service
        db_service.interval_minutes = interval_minutes
        db.commit()
        db.refresh(db_service)
        return db_service
    else:
        return None
    
def delete_s(db:Session, strid:str, vendor_id: str):
    db_service = db.query(Add_Service).filter(Add_Service.id == strid, Add_Service.vendor_id == str(vendor_id)).first()
    if db_service:
        db.delete(db_service)
        db.commit()
        return {"Service Deleted Successfully"}

def get_all_services(db:Session, vendor_id: str = None):
    if vendor_id:
        return db.query(Add_Service).filter(Add_Service.vendor_id == str(vendor_id)).all()
    return db.query(Add_Service).all()

def add_price_history(
    db: Session,
    service_id: str,
    add_vendor_id: str,
    price: float,
    request: SetServicePriceRequest,
):
    """Set BOTH full price AND booking fee atomically. Updates in place."""
    add_service = db.query(Add_Service).filter(
        Add_Service.id == service_id,
        Add_Service.vendor_id == str(add_vendor_id),
    ).first()
    if not add_service:
        raise HTTPException(404, "Service not found or you don't own it")
    
    # Q2: booking fee must be < full price
    if request.price_minor >= price:
        raise HTTPException(
            400, 
            f"Booking fee ({request.price_minor}) must be less than full price ({price})"
        )
    
    ph = _find_or_create_price_history(db, service_id, str(add_vendor_id))
    
    # Update — onupdate handles updated_at automatically
    ph.price = price
    ph.price_minor = to_minor_units(request.price_minor, request.currency)
    ph.currency = request.currency
    
    try:
        db.commit()
        db.refresh(ph)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update prices: {str(e)}")
    
    return ph

def get_price_history(db:Session, service_id:str, add_vendor_id:str):
    return db.query(price_history).filter(price_history.service_id == service_id, price_history.add_vendor_id == add_vendor_id).first()

def get_allprice_history(db:Session, vendor_id:str):
    results = (
        db.query(price_history, Add_Service.service_name, Add_Service.interval_minutes)
        .join(Add_Service, price_history.service_id == Add_Service.id)
        .filter(price_history.add_vendor_id == vendor_id)
        .all()
    )
    return [
        {
            "service_id" : ph.service_id,
            "id" : ph.id,
            "price": ph.price,
            "price_minor": ph.price_minor,
            "currency": ph.currency,
            "add_vendor_id": ph.add_vendor_id,
            "service_name": service_name,
            "interval_minutes": interval_minutes
        }
        for ph, service_name, interval_minutes in results
    ]

def update_price_history(db:Session, service_id:str, new_price:int):
    db_price = db.query(price_history).filter(price_history.id == service_id).first()
    if db_price:
        db_price.price = new_price
        db.commit()
        db.refresh(db_price)
        return db_price
    else:
        return None  # Price history with the given ID not found
    
def _find_or_create_price_history(db: Session, service_id: str, vendor_id: str) -> price_history:
    """One row per (service_id, vendor_id). Find or create empty one."""
    existing = db.query(price_history).filter(
        price_history.service_id == service_id,
        price_history.add_vendor_id == vendor_id,
    ).first()
    
    if existing:
        return existing
    
    new_entry = price_history(
        service_id=service_id,
        add_vendor_id=vendor_id,
        price=None,
        price_minor=0,
        currency=Currency.GHS,
    )
    db.add(new_entry)
    db.flush()  # Get the ID without committing yet
    return new_entry


def add_booking_price(
    db: Session,
    service_id: str,
    request: SetServicePriceRequest,
    vendor_id: str,
):
    """Set ONLY the booking fee. Updates price_history in place."""
    add_service = db.query(Add_Service).filter(
        Add_Service.id == service_id,
        Add_Service.vendor_id == str(vendor_id),
    ).first()
    if not add_service:
        raise HTTPException(404, "Service not found or you don't own it")
    
    ph = _find_or_create_price_history(db, service_id, str(vendor_id))
    
    new_fee_minor = to_minor_units(request.price_minor, request.currency)
    
    # Q9=a: Only validate if full price is set
    if ph.price is not None:
        full_price_minor = to_minor_units(ph.price, request.currency)
        if new_fee_minor >= full_price_minor:
            raise HTTPException(
                400, 
                f"Booking fee ({request.price_minor}) must be less than full price ({ph.price})"
            )
    
    # Update — onupdate handles updated_at automatically
    ph.price_minor = new_fee_minor
    ph.currency = request.currency
    
    try:
        db.commit()
        db.refresh(ph)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update booking fee: {str(e)}")
    
    return ph