from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
import app.modules.account_module as register_module
from app.modules.account_module import get_current_user
from app.config.db.postgresql import SessionLocal
from app.schemas import account_schema
from fastapi.security import OAuth2PasswordBearer,OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.models.account_model import User
from pydantic import EmailStr, BaseModel



router = APIRouter(prefix="/Account")


user_dependency = Annotated[str, Depends(get_current_user)]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Define the Pydantic model for request validation
class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", tags=["Account"])
async def register_user(register: account_schema.AccountCreateBase, db:Session=Depends(get_db)):
    responce = register_module.register_user(db=db, account=register)
    return responce

@router.post("/Login", tags=["Account"])
async def login_user(request: LoginRequest, db:Session=Depends(get_db)):
    responce = register_module.user_login(email=request.email, password=request.password, db=db)
    return responce

@router.put("update_password/{user_id}", tags=["Account"])
async def reset_password(update_passworda: account_schema.UpdatePassword, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    responce = register_module.reset_password(db=db, update_password=update_passworda, user_id=current_user.id)
    return responce

@router.post("/token", tags=["Account"], response_model=account_schema.Token)
async def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db:Session= Depends(get_db)):
    token = register_module.login_for_access_token(form_data=form_data, db=db)
    return token

@router.get("/welcome", tags=["Account"])
async def welcome_user(current_user : User = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user.email}, you are authorized"}










