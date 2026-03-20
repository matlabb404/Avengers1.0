from uuid import UUID
from sqlalchemy.orm import Session
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from app.models.service_model import Add_Service, price_history


def add_s(db:Session, strid:str ,service: services_schema.ServicesDropDownOption):
    db_service = Add_Service(id=strid,service_name=service)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return {"Service Added Successfully" :db_service}

def get_all_services(db:Session):
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
    return db.query(price_history).filter(price_history.add_vendor_id == vendor_id).all()

def update_price_history(db:Session, service_id:str, new_price:int):
    db_price = db.query(price_history).filter(price_history.id == service_id).first()
    if db_price:
        db_price.price = new_price
        db.commit()
        db.refresh(db_price)
        return db_price
    else:
        return None  # Price history with the given ID not found