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
    date_of_birth: datetime.datetime = Field(...)
    origin: str = Field(...)
    buyer: Optional[PyObjectId] = Field(default=None)
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    campaigns: List[PyObjectId] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@mail.com",
                "phone": "555-555-5555",
                "date_of_birth": "2020-01-01T00:00:00.000Z",
                "origin": "facebook",
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"],
                "buyer": "5f9c0a9e9c6d4b1e9c6d4b1e",
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
    date_of_birth: Optional[datetime.datetime] = None
    origin: Optional[str] = None
    buyer: Optional[PyObjectId] = Field(default=None)
    created_time: Optional[datetime.datetime] = None
    campaigns: Optional[List[PyObjectId]] = None
    custom_fields: Optional[dict] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "phone": "555-555-5555",
                "date_of_birth": "2020-01-01T00:00:00.000Z",
                "origin": "facebook",
                "buyer": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "created_time": "2020-01-01T00:00:00.000Z",
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e", "5f9c0a9e9c6d4b1e9c6d4b1e"],
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
