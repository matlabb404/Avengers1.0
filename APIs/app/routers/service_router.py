from fastapi import APIRouter, Depends
from typing import Annotated
from app.modules.service_module import add_s
import app.models.service_model as service_mdl
from app.schemas import services_schema
from app.config.db.postgresql import SessionLocal
from sqlalchemy.orm import Session



router = APIRouter(prefix="/Service")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/Add_service", tags=["Service"])
async def add_service(service: services_schema.ServicesDropDownOption, db:Session=Depends(get_db)):
    responce = add_s(db=db, service=service)
    return responce
