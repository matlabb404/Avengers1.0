from fastapi import APIRouter, Depends
from app.modules import customer_modules
from app.schemas import customer_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime


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