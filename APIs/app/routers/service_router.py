
from app.models.account_model import User
from app.modules.account_module import get_current_user
from app.modules.vendor_module import get_current_vendor
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import app.modules.big_services_module as big_service_mdl
from app.schemas import big_services_schema
from app.modules.service_module import add_s
import app.models.service_model as service_mdl
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
import hashlib,secrets,string
from datetime import timedelta



router = APIRouter(prefix="/Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/Add_service", tags=["Service"])
async def add_service(old_service: services_schema.ServicesDropDownOption, new_service: str, db:Session=Depends(get_db)):
    service = old_service
    if new_service != "None":
        service = new_service
    lowercase = service.lower()
    nospace = lowercase.replace(" ","")
    strid = nospace
    responce = add_s(db=db, strid= strid,service=service)
    return responce



@router.post("/Add_big_service", tags=["Big Service"])
async def add_big_service(big_service: big_services_schema.ServiceSchema, db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    vendor = get_current_vendor(current_user.id, db=db)
    response = big_service_mdl.add_service(db, big_service=big_service, add_vendor_id=vendor.vendor_id)
    response_with_vendor_id = {"vendor_id": vendor.vendor_id, "response": response}
    return response_with_vendor_id

@router.get("/get_service", tags=["Big Service"])
async def get_service(service_id: str, db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return db_service



@router.put("/update_service", tags=["Big Service"])
async def update_service(service_id: str, service_update: big_services_schema.ServiceUpdate, db: Session = Depends(get_db)):
    # Retrieve existing service data
    existing_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if existing_service is None:
        raise HTTPException(status_code=404, detail="Service not found")
    # Update service details
    for field, value in service_update.dict().items():
        setattr(existing_service, field, value)
    
    db.commit()
    db.refresh(existing_service)
    return existing_service

'''

@router.delete("/delete_service/{service_id}", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    db_service = big_service_mdl.get_service(db=db, service_id=service_id)
    if db_service is None:
        return "Not Found"
    return big_service_mdl.delete_service(db=db, service=db_service)
'''
@router.delete("/delete_service", tags=["Big Service"])
async def delete_service(service_id: str, db: Session = Depends(get_db)):
    deleted = big_service_mdl.delete_service(db=db, service_id=service_id)
    if deleted:
        return {"message": "Service deleted successfully"}
    else:
        return {"message": "Service not found"}
    
@router.get("/get_all_service_by_vendor", tags=["Big Service"])
async def get_all_service_by_vendor(vendor_id: str, db:Session= Depends(get_db)):
    service = big_service_mdl.get_service_by_vendor(db=db, vendor_id=vendor_id)
    return service