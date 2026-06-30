from uuid import UUID
from pydantic import BaseModel


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str   # "ANDROID" | "IOS"


class RegisterTokenResponse(BaseModel):
    ok: bool


class UnregisterTokenRequest(BaseModel):
    token: str