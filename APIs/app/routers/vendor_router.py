from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from typing import Annotated
import app.modules.vendor_module as vendor_mdl
import app.modules.booking_module as booking_module
import app.models.account_model as acct_mdl
import app.modules.account_module as acct_module
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas.vendor_Schema import Gender
from app.models.account_model import User
from app.modules.account_module import get_current_user
from datetime import timedelta, date
import hashlib,secrets,string

router = APIRouter(prefix="/Vendor")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_vendor", tags=["Vendor"])
async def add_vendor( vendor: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db),  current_user : User = Depends(get_current_user)):
    email = current_user.email
    user_id = current_user.id
    responce = vendor_mdl.add_vendor(db=db, vendor=vendor, vendor_emaail = email, user_id_=user_id)
    return responce

@router.get("/get_vendor", tags=["Vendor"])
async def get_vendor(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    vendor_record = vendor_mdl.get_current_vendor(current_user.id, db=db)
    if not vendor_record:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor_record

@router.post("/Vendor_Details", tags=["Vendor"])
async def vendor_details( vendor_detials_request: vendor_Schema.VendorDetailsCreateBase, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.add_vendor_details(db=db, vendor_id = vendor.vendor_id ,vendor_details_request=vendor_detials_request)
    return response

@router.put("/Update_Vendor", tags=["Vendor"])
async def update_vendor(vendor_update: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.vendor_update(db=db, vendor_id= vendor.vendor_id ,vendor_update=vendor_update)
    return response

@router.delete("/Delete_Vendor", tags=["Vendor"])
async def delete_vendor(db:Session=Depends(get_db),current_user : User = Depends(get_current_user)):
    vendor = vendor_mdl.get_current_vendor( current_user.id, db=db)
    response = vendor_mdl.vendor_delete(db=db, vendor_id=vendor.vendor_id)
    return response

@router.delete("/Delete_Vendor_details", tags=["Vendor"])
async def delete_vendor(vendor_id_details: UUID , db:Session=Depends(get_db),current_user : User = Depends(get_current_user)):
    response = vendor_mdl.vendor_delete(db=db, vendor_id=vendor_id_details)
    return response

@router.get("/get_all_vendors", tags=["Vendor"])
async def get_all_vendors():
    all_vendors = vendor_mdl.get_all_vendors()
    return all_vendors

@router.get("/get_gender_vendors", tags=["Vendor"])
async def get_gender_vendors(gender:Gender):
    gender_vendors = vendor_mdl.get_gender_vendors(gender)
    return gender_vendors

# ---- Scheduling ---- 
@router.get("/get_schedule/{vendor_id}", tags=["Vendor"])
async def read_schedule(vendor_id: str, db: Session = Depends(get_db)):
    schedule = vendor_mdl.get_schedule(db, vendor_id)

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule

@router.post("/schedule/{vendor_id}", tags=["Vendor"])
async def upsert_schedule(
    vendor_id: str,
    data: dict,
    db: Session = Depends(get_db)
):
    return vendor_mdl.create_or_update_schedule(db, vendor_id, data)

# ---- Availability ----
@router.get("/{vendor_id}/availability", tags=["Vendor"])
async def get_availability(
    vendor_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    schedule = vendor_mdl.get_schedule(db, vendor_id)

    if not schedule:
        return []

    exceptions = vendor_mdl.get_exceptions(db, vendor_id, start_date, end_date)

    return booking_module.generate_slots(schedule, exceptions, start_date, end_date)


# ---- Exceptions ----
@router.post("/add_exception", tags=["Vendor"])
def create_exception_endpoint(data: dict, db: Session = Depends(get_db)):
    return vendor_mdl.create_exception(db, data)


@router.get("/{vendor_id}/exceptions", tags=["Vendor"])
def read_exceptions(
    vendor_id: str,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    return vendor_mdl.get_exceptions(db, vendor_id, start_date, end_date)


@router.delete("/{exception_id}/delete_exception", tags=["Vendor"])
def delete_exception_endpoint(
    exception_id: str,
    db: Session = Depends(get_db)
):
    return vendor_mdl.delete_exception(db, exception_id)