from fastapi import APIRouter, Depends, HTTPException
from app.modules import customer_modules
from app.models import customer_model
from app.schemas import customer_schema
from app.models.customer_model import customer
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Any, Dict


router = APIRouter(prefix="/customer")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/Add_customer", tags=["customer"])
async def add_customer(customer: customer_schema.CustomerCreateBase, db:Session=Depends(get_db)):
    # Add today's date to the 'last_edited' field
    customer.last_edited = datetime.now()
    response = customer_modules.add_customer(db=db, customer=customer)
    return response


@router.put("/update_customer/{customer_id}", tags=["customer"])
async def update_customer(customer_id: int, update_data: customer_schema.CustomerUpdate, db: Session = Depends(get_db)):
    # Retrieve existing customer data
    existing_customer = db.query(customer).filter(customer.customer_id == customer_id).first()
    if existing_customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")  
    # Update customer details
    for field, value in update_data.dict().items():
        setattr(existing_customer, field, value)
    
    db.commit()
    db.refresh(existing_customer)
    return existing_customer


@router.delete("/delete_customer/{customer_id}", tags=["customer"])
async def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    deleted = customer_modules.delete_customer_by_id(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}