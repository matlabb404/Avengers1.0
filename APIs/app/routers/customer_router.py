from fastapi import APIRouter, Depends, HTTPException
from app.modules import customer_modules
from app.models import customer_model
from app.schemas import customer_schema
from app.modules.account_module import get_current_user
from app.models.customer_model import customer
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime,timedelta
from app.models.account_model import User
from typing import Any, Dict
import hashlib,secrets,string
import uuid


router = APIRouter(prefix="/customer")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_customer", tags=["customer"])
async def add_customer(customer: customer_schema.CustomerCreateBase, db:Session=Depends(get_db), current_user : User= Depends(get_current_user)):
    user_ida = current_user.id
    customer.last_edited = datetime.now() # Add today's date to the 'last_edited' field
    response = customer_modules.add_customer(db=db, customer=customer, user_id_=user_ida)
    return response


@router.put("/update_customer", tags=["customer"])
async def update_customer( updated_data: customer_schema.CustomerUpdate, db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    # Retrieve existing customer data
    existing_customer = customer_modules.update_customer_id(db=db, current_user_id=current_user.id, update_data=updated_data)
    return existing_customer


@router.delete("/delete_customer", tags=["customer"])
async def delete_customer(db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    customer_id = customer_modules.get_current_customer( current_user.id, db=db).customer_id
    deleted = customer_modules.delete_customer_by_id(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}