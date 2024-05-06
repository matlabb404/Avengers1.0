from sqlalchemy.orm import Session
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from app.models.service_model import Add_Service


def add_s(db:Session, service:services_schema.ServicesDropDownOption):
    db_service = Add_Service(service_name=service)
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return {"Service Added Successfully" }