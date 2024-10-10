import datetime
import math
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict, computed_field, root_validator
from pydantic import validator, field_validator
from typing import List, Optional, Dict, Any

from app.tools.modifiers import PyObjectId


class CRMModel(BaseModel):
    """
    Container for a single CRM record.
    """
    name: Optional[str] = Field(default=None)
    url: Optional[str] = Field(default=None)
    integration_details: Optional[Dict[str, Any]] = Field(default=None)

    @root_validator(pre=True)
    def replace_invalid_with_empty_string(cls, values):
        integration_details = values.get('integration_details', {})
        if isinstance(integration_details, dict):
            for key, value in integration_details.items():
                if isinstance(value, float) and math.isnan(value):
                    integration_details[key] = ""
        values['integration_details'] = integration_details
        return values

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Ringy",
                "url": "www.ringy.com",
                "integration_details": {
                    "auth_token": "value1",
                    "sid": "value2"
                }
            }
        }
    )


class CRMCollection(BaseModel):
    """
    A container holding a list of `CRMModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    CRMs: List[CRMModel]


class AgentCredentials(BaseModel):
    """
    A container holding the data needed to deliver a lead to a Agent.
    """
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)


class AgentModel(BaseModel):
    """
    Container for a single Agent record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    phone: str = Field(...)
    states_with_license: List = Field(...)
    CRM: CRMModel = Field(default_factory=CRMModel)
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    campaigns: List[PyObjectId] = Field(default_factory=list)
    credentials: AgentCredentials = Field(default_factory=AgentCredentials)
    custom_fields: Optional[dict] = Field(default=None)

    @validator('phone', pre=True, always=True)
    def ensure_phone_is_str(cls, v):
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator('campaigns', mode='before')
    def validate_campaigns(cls, v):
        if isinstance(v, list):
            return [PyObjectId(i) if not isinstance(i, ObjectId) else i for i in v]
        raise ValueError('Invalid campaigns list')

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
                "email": "janedoe@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"],
                "custom_fields": {}
            }
        }
    )

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data


class UpdateAgentModel(BaseModel):
    """
    A set of optional updates to be made to a Agent document in the database.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    states_with_license: Optional[List] = None
    CRM: Optional[CRMModel] = Field(default=None)
    created_time: Optional[datetime.datetime] = None
    campaigns: Optional[List[PyObjectId]] = None
    credentials: Optional[AgentCredentials] = None
    custom_fields: Optional[dict] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "creation_time": "2020-01-01T00:00:00.000Z",
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e", "324sddsds"],
                "custom_fields": {}
            }
        }
    )


class AgentCollection(BaseModel):
    """
    A container holding a list of `AgentModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    data: List[AgentModel]
