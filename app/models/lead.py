import datetime
import math
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict, computed_field, root_validator, validator
from typing import List, Optional

from app.tools.modifiers import PyObjectId


class LeadModel(BaseModel):
    """
    Container for a single Lead record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: Optional[str] = Field(...)
    email: Optional[str] = Field(...)
    phone: Optional[str] = Field(...)
    state: Optional[str] = Field(...)
    origin: Optional[str] = Field(...)
    last_name: Optional[str] = Field(...)
    buyer_id: Optional[PyObjectId] = Field(default=None)
    second_chance_buyer_id: Optional[PyObjectId] = Field(default=None)
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    lead_sold_time: Optional[datetime.datetime] = Field(default=None)
    second_chance_lead_sold_time: Optional[datetime.datetime] = Field(default=None)
    lead_sold_by_agent_time: Optional[datetime.datetime] = Field(default=None)
    lead_sold_by_integrity: Optional[datetime.datetime] = Field(default=None)
    lead_received_date: Optional[datetime.datetime] = None
    lead_type: Optional[str] = None
    campaign_id: PyObjectId = Field(...)
    is_second_chance: bool = Field(default=False)
    custom_fields: Optional[dict] = Field(default=None)

    @validator('phone', pre=True, always=True)
    def ensure_phone_is_str(cls, v):
        if isinstance(v, int):
            return str(v)
        return v

    @root_validator(pre=True)
    def replace_invalid_with_empty_string(cls, values):
        custom_fields = values.get('custom_fields', {})
        if isinstance(custom_fields, dict):
            for key, value in custom_fields.items():
                if isinstance(value, float) and math.isnan(value):
                    custom_fields[key] = ""
        values['custom_fields'] = custom_fields
        return values
    @root_validator(pre=True)
    def strip_fields(cls, values):
        fields_to_strip = ['first_name', 'last_name', 'phone', 'email']
        for field in fields_to_strip:
            if field in values and isinstance(values[field], str):
                values[field] = values[field].strip()
        return values
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

    @computed_field
    @property
    def full_name(self) -> str:
        return str(self.first_name + " " + self.last_name)

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data


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
    lead_sold_by_agent_time: Optional[datetime.datetime] = None
    lead_received_date: Optional[datetime.datetime] = None
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
                "lead_sold_by_agent_time": "2020-01-01T00:00:00.000Z",
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
    data: List[LeadModel]
