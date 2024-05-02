from fastapi import APIRouter, Depends
import app.modules.vendor_module as vendor_mdl
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session


router = APIRouter(prefix="/Vendor")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_vendor", tags=["Vendor"])
async def add_vendor(vendor: vendor_Schema.VendorCreateBase, db:Session=Depends(get_db)):
    responce = vendor_mdl.add_vendor(db=db, vendor=vendor)
    return responce