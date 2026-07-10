from pydantic import BaseModel,EmailStr
from typing import Union


class AccountCreateBase(BaseModel):
    email: EmailStr
    password: str
    confirm_password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str      # <-- must be present, or the client never receives it
    token_type: str

class TokenData(BaseModel):
    email : str

class UserOut(BaseModel):
    email: EmailStr

class UpdatePassword(BaseModel):
    new_password: str
    confirm_new_password: str

# ── Refresh: rotate refresh token, mint a fresh access token ──────────────────
class RefreshRequest(BaseModel):
    refresh_token: str

# ── Logout: revoke the refresh token (real server-side logout) ────────────────
class LogoutRequest(BaseModel):
    refresh_token: str