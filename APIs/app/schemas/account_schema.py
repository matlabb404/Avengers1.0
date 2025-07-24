from pydantic import BaseModel,EmailStr
from typing import Union


class AccountCreateBase(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

class Token(BaseModel):
    access_token : str 
    token_type: str 

class TokenData(BaseModel):
    email : str


class UserOut(BaseModel):
    email: EmailStr

class UpdatePassword(BaseModel):
    new_password: str
    confirm_new_password: str