from pydantic import BaseModel
from typing import Dict, Union


class Name(BaseModel):
    id: int
    name: str 
