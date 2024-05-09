import requests
import aioredis
from app.models import vendor_model, api_test_model
from sqlalchemy.orm import Session
import json
from app.schemas import vendor_Schema
from app.config.db.postgresql import SessionLocal
from app.models.vendor_model import Vendor
from sqlalchemy.dialects import postgresql
from uuid import UUID


def add_vendor(db:Session, vendor:vendor_Schema.VendorCreateBase ):

    db_vendor = vendor_model.Vendor(**vendor.dict())
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)
    return db_vendor.vendor_id
    #return db_vendor.vendor_id.compile(dialect=postgresql.dialect())


def gett(name: str):
    responcedata = requests.get("http://127.0.0.1:8000/Account/register")
    return responcedata.status_code


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