from enum import Enum
from pydantic import BaseModel, Field
from app.models.payment_model import Currency

class ServicesDropDownOption(str, Enum):
    hairdye = "Hair Dye"
    hairstyling = "Hair Styling"
    hairtrimming = "Hair Trimming"
    haircutting = "Hair Cutting"
    hairwashing = "Wash Hair"
    relaxhair = "Relax Hair"


class SetServicePriceRequest(BaseModel):
    price_minor: float = Field(..., ge=0, description="Price in major units (e.g., 50.00 for ¢50)")
    currency: Currency = Currency.GHS