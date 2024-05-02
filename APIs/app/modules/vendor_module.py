from app.models import vendor_model, api_test_model
from sqlalchemy.orm import Session
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal




def add_vendor(db:Session,  vendor:vendor_Schema.VendorCreateBase ):
    db_vendor = vendor_model.Vendor(**vendor.dict())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor