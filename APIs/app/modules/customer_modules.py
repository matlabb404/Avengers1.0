from app.models import customer_model
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas import customer_schema
from typing import Any, Dict



def add_customer(db:Session,  customer:customer_schema.CustomerCreateBase ):
    db_customer = customer_model.customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def update_customer_id(db: Session, customer_id: int, update_data: dict):
    db_customer = db.query(customer_model.customer).filter(customer_model.customer.customer_id == customer_id).first()
    if db_customer:
        for key, value in update_data.dict().items():  
            setattr(db_customer, key, value)
        db.commit()
        db.refresh(db_customer)
        return db_customer
    else:
        return None  # Customer with the given ID not found


def delete_customer_by_id(db: Session, customer_id: int):
    customer = db.query(customer_model.customer).filter(customer_model.customer.customer_id == customer_id).first()
    if customer:
        db.delete(customer)
        db.commit()
        return True
    else:
        return False