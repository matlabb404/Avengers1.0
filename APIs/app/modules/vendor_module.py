from app.models import vendor_model, api_test_model
from sqlalchemy.orm import Session
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from app.models.vendor_model import Vendor


def add_vendor(db:Session, vendor:vendor_Schema.VendorCreateBase ):
    db_vendor = vendor_model.Vendor(**vendor.dict())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor

def get_all_vendors():
    session_get = SessionLocal()
    all_vendors = session_get.query(Vendor).all()
    return all_vendors

def get_gender_vendors(gender):
    session_get = SessionLocal()
    all_vendors = session_get.query(Vendor).filter(Vendor.gender == gender).all()
    return all_vendors