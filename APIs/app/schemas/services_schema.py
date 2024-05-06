from enum import Enum
from pydantic import BaseModel

class ServicesDropDownOption(str, Enum):
    service1 = "Hair Dye"
    service2 = "Hair Styling"
    service3 = "Hair Trimming"
    service4 = "Hair Cutting"
    service5 = "Wash Hair"
    service6 = "Relax Hair"
    service7 = "Option 3"
    service8 = "Option 3"
    service9 = "Option 3"
    service10 = "Option 3"

