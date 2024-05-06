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
    email : Union[str, None] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        orm_mode = True

