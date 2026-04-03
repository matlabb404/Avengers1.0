from app.models import service_model
from app.schemas import big_services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.big_services_schema import ServiceUpdate
from app.models.vendor_model import Vendor
from fastapi import APIRouter, Depends, HTTPException
from app.models.service_model import Service
from app.modules.service_module import get_price_history, get_allprice_history, update_price_history
import uuid

def add_service(db: Session, big_service: big_services_schema.ServiceUpdate, add_vendor_id: str):
    #if not db.query(Vendor).filter(Vendor.vendor_id == add_vendor_id).first():
    #    raise HTTPException(status_code=404, detail="Vendor not found")
    new_service = Service(
        add_vendor_id=add_vendor_id,
        price=big_service.price,
        price_history=big_service.price_history,
        add_service_id=big_service.add_service_id,
        image_url=big_service.image_url,  
        description=big_service.description
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    price_history = get_price_history(db=db, service_id=big_service.add_service_id, add_vendor_id=add_vendor_id)
    return {"service": new_service, "price": price_history}

def get_service(db: Session, service_id: str):
    db_servce = db.query(service_model.Service, Vendor, service_model.price_history, service_model.Add_Service).join(service_model.Add_Service, service_model.Service.add_service_id == service_model.Add_Service.id).join(Vendor, service_model.Service.add_vendor_id == Vendor.vendor_id).join(service_model.price_history, service_model.Service.price_history ==  service_model.price_history.id).filter(service_model.Service.id == service_id).first()
    if not db_servce:
        raise HTTPException(status_code=404, detail="Service not found")
    
    service, vendor, price_history, add_service = db_servce
    return {
        "service": {
            "id": service.id,
            "price": service.price,
            "description": service.description,
            "image_url": service.image_url,
            "add_vendor_id": service.add_vendor_id,
            "add_service_id": service.add_service_id
        },
        "vendor": {
            "vendor_id": vendor.vendor_id,
            "first_name": vendor.first_name,
            "last_name": vendor.last_name,
            "business_name": vendor.business_name,
            "city": vendor.city,
            "country": vendor.country
        },
        "add_service": {
            "id": add_service.id,
            "service_name": add_service.service_name
        },
        "price_history": {
            "id": price_history.id,
            "price": price_history.price
        }
}

def update_service(db: Session, service_id: str, update_data: ServiceUpdate):
    db_service = db.query(service_model.Service).filter(service_model.Service.id == service_id).first()
    if db_service:
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(db_service, key, value)
        db.commit()
        db.refresh(db_service)
        price_history = get_price_history(db=db, service_id=db_service.add_service_id, add_vendor_id=db_service.add_vendor_id)
        return {"service": db_service, "price": price_history}
    else:
        return None  # Service with the given ID not found
    
def delete_service(db: Session, service_id: str):
    db_service = db.query(service_model.Service).filter(service_model.Service.id == service_id).first()
    if db_service:
        db.delete(db_service)
        db.commit()
        return True
    else:
        return False
    
def get_service_by_vendor(db:Session, vendor_id : str):
    db_servce = db.query(service_model.Service, Vendor, service_model.price_history, service_model.Add_Service).join(service_model.Add_Service, service_model.Service.add_service_id == service_model.Add_Service.id).join(Vendor, service_model.Service.add_vendor_id == Vendor.vendor_id).join(service_model.price_history, service_model.Service.price_history ==  service_model.price_history.id).filter(service_model.Service.add_vendor_id == vendor_id).all()
    output = []

    for service, vendor, price_history, add_service in db_servce:
        output.append({
            "service": {
                "id": service.id,
                "price": service.price,
                "description": service.description,
                "image_url": service.image_url,
                "add_vendor_id": service.add_vendor_id,
                "add_service_id": service.add_service_id
            },
            "vendor": {
                "vendor_id": vendor.vendor_id,
                "first_name": vendor.first_name,
                "last_name": vendor.last_name,
                "business_name": vendor.business_name,
                "city": vendor.city,
                "country": vendor.country
            },
            "add_service": {
                "id": add_service.id,
                "service_name": add_service.service_name
            },
            "price_history": {
                "id": price_history.id,
                "price": price_history.price
            }
        })
    return output

def get_all_service(db:Session):
    db_servce = db.query(service_model.Service, Vendor, service_model.price_history, service_model.Add_Service).join(service_model.Add_Service, service_model.Service.add_service_id == service_model.Add_Service.id).join(Vendor, service_model.Service.add_vendor_id == Vendor.vendor_id).join(service_model.price_history, service_model.Service.price_history ==  service_model.price_history.id).all()
    output = []

    for service, vendor, price_history, add_service in db_servce:
        output.append({
            "service": {
                "id": service.id,
                "price": service.price,
                "description": service.description,
                "image_url": service.image_url,
                "add_vendor_id": service.add_vendor_id,
                "add_service_id": service.add_service_id
            },
            "vendor": {
                "vendor_id": vendor.vendor_id,
                "first_name": vendor.first_name,
                "last_name": vendor.last_name,
                "business_name": vendor.business_name,
                "city": vendor.city,
                "country": vendor.country
            },
            "add_service": {
                "id": add_service.id,
                "service_name": add_service.service_name
            },
            "price_history": {
                "id": price_history.id,
                "price": price_history.price
            }
        })
    return output

# TODO: Change to use ORM relationships (.joinedload)