from fastapi import APIRouter
import app.modules.account_module as register_module
from pydantic import EmailStr



router = APIRouter(prefix="/Accounts")

@router.get("/register", tags=["Account"])
async def register_user(email: EmailStr, password: str, confirm_password: str):
    responce = register_module.register_user(email, password, confirm_password)
    return responce
