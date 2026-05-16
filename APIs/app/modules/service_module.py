from uuid import UUID
from app.schemas.booking_schema import SetServicePriceRequest
from sqlalchemy.orm import Session
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from app.models.service_model import Add_Service, price_history
from app.utils.money import to_minor_units, from_minor_units
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

def add_price_history(db:Session, service_id:str, add_vendor_id:str, price:int):
    new_price = price_history(service_id=service_id, price=price, add_vendor_id=add_vendor_id)
    db.add(new_price)
    db.commit()
    db.refresh(new_price)
    return new_price

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
    
def add_booking_price(
    db: Session, 
    service_id: str, 
    request: SetServicePriceRequest, 
    vendor_id: str
):
    """
    Update the booking price for a service AND log the change to price_history.
    The Add_Service row is the source of truth; price_history is the audit trail.
    """
    # 1. Verify ownership
    add_service = db.query(Add_Service).filter(
        Add_Service.id == service_id,
        Add_Service.vendor_id == str(vendor_id)
    ).first()
    
    if not add_service:
        raise HTTPException(404, "Service not found or you don't own it")
    
    # 2. Convert to minor units (pesewas/kobo)
    new_price_minor = to_minor_units(request.price, request.currency)
    old_price_minor = add_service.price_minor
    
    # 3. Skip if nothing changed (avoid noise in audit log)
    if (new_price_minor == old_price_minor 
        and add_service.currency == request.currency):
        return {
            "service_id": add_service.id,
            "service_name": add_service.service_name,
            "price": from_minor_units(add_service.price_minor, add_service.currency),
            "currency": add_service.currency.value,
            "price_minor": add_service.price_minor,
            "changed": False,
            "message": "Price unchanged",
        }
    
    # 4. Update Add_Service (source of truth for current price)
    add_service.price_minor = new_price_minor
    add_service.currency = request.currency
    
    # 5. Log to price_history (audit trail)
    history_entry = price_history(
        service_id=service_id,
        add_vendor_id=vendor_id,
        price=request.price,
        price_minor=new_price_minor,                    # ✅ NEW
        currency=request.currency,                       # ✅ NEW
        # changed_by_user_id=current_user.id,           if you pass user in
    )
    db.add(history_entry)
    
    # 6. Commit atomically - either both succeed or both roll back
    try:
        db.commit()
        db.refresh(add_service)
        db.refresh(history_entry)
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update price: {str(e)}")
    
    return {
        "service_id": add_service.id,
        "service_name": add_service.service_name,
        "price": from_minor_units(add_service.price_minor, add_service.currency),
        "currency": add_service.currency.value,
        "price_minor": add_service.price_minor,
        "history_id": str(history_entry.id),
        "previous_price_minor": old_price_minor,
        "changed": True,
    }