from app.models import service_model
from app.schemas import big_services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.big_services_schema import ServiceUpdate
from app.models.vendor_model import Vendor
from fastapi import APIRouter, Depends, HTTPException
from app.models.service_model import Service
import uuid

def add_service(db: Session, big_service: big_services_schema.ServiceSchema, add_vendor_id: str):
    #if not db.query(Vendor).filter(Vendor.vendor_id == add_vendor_id).first():
    #    raise HTTPException(status_code=404, detail="Vendor not found")
    new_service = Service(
        add_vendor_id=add_vendor_id,
        price=big_service.price,
        add_service_id=big_service.add_service_id
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

def get_service(db: Session, service_id: str):
    return db.query(service_model.Service).filter(service_model.Service.id == service_id).first()


def update_service(db: Session, service_id: str, update_data: ServiceUpdate):
    db_service = db.query(service_model.Service).filter(service_model.Service.id == service_id).first()
    if db_service:
        for key, value in update_data.dict().items():
            setattr(db_service, key, value)
        db.commit()
        db.refresh(db_service)
        return db_service
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
    db_servce = db.query(service_model.Service).filter(service_model.Service.add_vendor_id == vendor_id).all()
    return db_servce