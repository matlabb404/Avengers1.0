from app.models import customer_model
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session
from app.schemas import customer_schema


def add_customer(db:Session,  customer:customer_schema.CustomerCreateBase ):
    db_customer = customer_model.customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer