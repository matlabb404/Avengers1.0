from pydantic import BaseModel
from datetime import date, datetime


class CustomerCreateBase(BaseModel):
    name : str
    address_1 : str
    address_2 : str
    city : str
    post_code : str
    country : str
    date_of_birth : date
    last_edited: datetime = None  # Default value is None