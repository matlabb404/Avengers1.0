from enum import Enum
from pydantic import BaseModel

class ServicesDropDownOption(str, Enum):
    hairdye = "Hair Dye"
    hairstyling = "Hair Styling"
    hairtrimming = "Hair Trimming"
    haircutting = "Hair Cutting"
    hairwashing = "Wash Hair"
    relaxhair = "Relax Hair"

