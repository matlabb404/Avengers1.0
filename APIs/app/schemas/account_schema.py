from pydantic import BaseModel,EmailStr

class AccountCreateBase(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str
