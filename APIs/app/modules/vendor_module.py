from app.models import vendor_model, api_test_model
from sqlalchemy.orm import Session
import json
from app.models.account_model import User
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from app.models.vendor_model import Vendor
from sqlalchemy.dialects import postgresql
from uuid import UUID


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


# def gett(name: str):
#     responcedata = requests.get("http://127.0.0.1:8000/Account/register")
#     return responcedata.status_code


def add_vendor_details(db:Session, vendor_id: UUID ,vendor_details_request:vendor_Schema.VendorDetailsCreateBase):
    db_vendor_details = vendor_model.Vendor_Details(vendor_id_details=vendor_id,
                                       description=vendor_details_request.description,
                                       picture_url=vendor_details_request.picture_url,
                                       review=vendor_details_request.review)
    db.add(db_vendor_details)
    db.commit()
    db.refresh(db_vendor_details)
    return db_vendor_details

def get_all_vendors():
    session_get = SessionLocal()
    all_vendors = session_get.query(Vendor).all()
    return all_vendors

def get_gender_vendors(gender):
    session_get = SessionLocal()
    all_vendors = session_get.query(Vendor).filter(Vendor.gender == gender).all()
    return all_vendors

### FOR SCHEDULING NOW
def __schedule(db:Session, schedule_vendor_id: UUID, schedulebase:vendor_Schema.Scheduling):
    scheduling = vendor_model.Scheduling_(schedule_vendor_id = schedule_vendor_id,
                                       days = schedulebase.days,
                                       exceptions = schedulebase.exceptions)
    db.add(scheduling)
    db.commit()
    db.refresh(scheduling)
    return scheduling


def get_current_vendor(user_id: str, db: Session ):
    vendor = db.query(vendor_model.Vendor).filter(vendor_model.Vendor.user_id == user_id).first()
    return vendor