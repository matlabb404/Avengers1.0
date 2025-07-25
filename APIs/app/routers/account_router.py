from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from app.models import customer_model, vendor_model
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

class CustomerExistsResponse(BaseModel):
    exists: bool
    user_id: str    

@router.post("/register", tags=["Account"])
async def register_user(register: account_schema.AccountCreateBase, db:Session=Depends(get_db)):
    responce = {register_module.register_user(db=db, account=register)}
    return responce

@router.post("/Login", tags=["Account"])
async def login_user(request: LoginRequest,db:Session=Depends(get_db)):
    user = register_module.user_login(email=request.email, password=request.password, db=db)
    access_token = register_module.login_for_access_token(form_data=request, db=db)
    responce = {"user": user, "id_token": access_token}
    return responce

@router.put("update_password/{user_id}", tags=["Account"])
async def reset_password(update_passworda: account_schema.UpdatePassword, db:Session=Depends(get_db), current_user : User = Depends(get_current_user)):
    responce = {register_module.reset_password(db=db, update_password=update_passworda, user_id=current_user.id)}
    return responce

@router.post("/token", tags=["Account"], response_model=account_schema.Token)
async def get_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db:Session= Depends(get_db)):
    token = register_module.login_for_access_token(form_data=form_data, db=db)
    return token

@router.get("/user/exists", tags=["Account"])
async def check_customer_exists( db: Session = Depends(get_db), current_user : User = Depends(get_current_user)):
    user_id = current_user.id
    customer = db.query(customer_model.customer).filter(customer_model.customer.user_id == user_id).first()
    vendor = db.query(vendor_model.Vendor).filter(vendor_model.Vendor.user_id == user_id).first()
    ans = {"bool": False, "customer": False, "vendor": False}
    if customer:
        ans["customer"], ans["bool"] = True, True
    if vendor:
        ans["vendor"], ans["bool"] = True, True
    return ans
    

@router.get("/welcome", tags=["Account"])
async def welcome_user(current_user : User = Depends(get_current_user)):
    return {"message": f"Welcome, {current_user.email}, you are authorized"}

@router.get("/get_user", tags=["Account"])
async def get_user_wtoken(token:str):
    user = {register_module.get_current_user(token=token)}
    if ( user == {"detail": "User not found"}):
        return False
    return True