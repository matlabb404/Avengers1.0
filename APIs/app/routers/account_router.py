from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import app.modules.account_module as register_module
from app.modules.account_module import get_current_user
from app.config.db.postgresql import SessionLocal
from app.schemas import account_schema
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models.account_model import User
from pydantic import EmailStr



router = APIRouter(prefix="/Account")


user_dependency = Annotated[dict, Depends(get_current_user)]


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

@router.post("/Login", tags=["Account"])
async def login_user(email, password, db:Session=Depends(get_db)):
    responce = register_module.user_login(email=email, password=password, db=db)
    return responce

@router.post("/token", tags=["Account"])
async def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db:Session= Depends(get_db)):
    token = register_module.login_for_access_token(form_data=form_data, db=db)
    return token

@router.get("/example", tags=["Account"])
async def example(email: str = Depends(get_current_user)):
    return {"email" : email}

