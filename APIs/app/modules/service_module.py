from uuid import UUID
from sqlalchemy.orm import Session
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from app.models.service_model import Add_Service, price_history


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

def get_all_services(db:Session):
    return db.query(Add_Service).all()

def get_all_services(db:Session, vendor_id:str):
    return db.query(Add_Service).filter(Add_Service.vendor_id == str(vendor_id)).all()

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
        db.query(price_history, Add_Service.service_name)
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
            "service_name": service_name
        }
        for ph, service_name in results
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