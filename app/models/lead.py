import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import List, Optional, Annotated


PyObjectId = Annotated[str, BeforeValidator(str)]


class LeadModel(BaseModel):
    """
    Container for a single Lead record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    state: str = Field(...)
    origin: str = Field(...)
    buyer_id: Optional[PyObjectId] = Field(default=None)
    second_chance_buyer_id: Optional[PyObjectId] = Field(default=None)
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    lead_sold_time: Optional[datetime.datetime] = Field(default=None)
    second_chance_lead_sold_time: Optional[datetime.datetime] = Field(default=None)
    campaign_id: PyObjectId = Field(...)
    is_second_chance: bool = Field(default=False)
    custom_fields: Optional[dict] = Field(default=None)  # dict = Field(default_factory=dict)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@mail.com",
                "phone": "555-555-5555",
                "state": "CA",
                "origin": "facebook",
                "campaign_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "buyer_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "second_chance_buyer_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "created_time": "2020-01-01T00:00:00.000Z",
                "lead_sold_time": "2020-01-01T00:00:00.000Z",
                "second_chance_lead_sold_time": "2020-01-01T00:00:00.000Z",
                "is_second_chance": False,
                "custom_fields": {
                    "field1": "value1",
                    "field2": "value2"
                }
            }
        }
    )


class UpdateLeadModel(BaseModel):
    """
    A set of optional updates to be made to a Lead document in the database.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    origin: Optional[str] = None
    buyer_id: Optional[PyObjectId] = Field(default=None)
    second_chance_buyer_id: Optional[PyObjectId] = Field(default=None)
    created_time: Optional[datetime.datetime] = None
    lead_sold_time: Optional[datetime.datetime] = None
    second_chance_lead_sold_time: Optional[datetime.datetime] = None
    campaign_id: PyObjectId = None
    is_second_chance: Optional[bool] = None
    custom_fields: Optional[dict] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@mail.com",
                "phone": "555-555-5555",
                "state": "CA",
                "origin": "facebook",
                "campaign_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "buyer_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "second_chance_buyer_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "created_time": "2020-01-01T00:00:00.000Z",
                "lead_sold_time": "2020-01-01T00:00:00.000Z",
                "second_chance_lead_sold_time": "2020-01-01T00:00:00.000Z",
                "is_second_chance": False,
                "custom_fields": {
                    "field1": "value1",
                    "field2": "value2"
                }
            }
        }
    )


class LeadCollection(BaseModel):
    """
    A container holding a list of `LeadModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    leads: List[LeadModel]
