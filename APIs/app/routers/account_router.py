from fastapi import APIRouter, Depends
import app.modules.account_module as register_module
from app.config.db.postgresql import SessionLocal
from app.schemas import account_schema
from sqlalchemy.orm import Session
from pydantic import EmailStr



router = APIRouter(prefix="/Account")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register", tags=["Account"])
async def register_user(register: account_schema.AccountCreateBase, db:Session=Depends(get_db)):
    responce = register_module.register_user(db=db, account=register)
    return responce