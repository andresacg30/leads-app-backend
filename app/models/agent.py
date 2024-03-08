import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import List, Optional, Annotated


PyObjectId = Annotated[str, BeforeValidator(str)]


class AgentCredentials(BaseModel):
    """
    A container holding the data needed to deliver a lead to a Agent.
    """
    id_token: Optional[str] = Field(default=None)
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
    CRM: Optional[PyObjectId] = Field(default=None)
    created_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    campaigns: List[PyObjectId] = Field(default_factory=list)
    credentials: AgentCredentials = Field(default_factory=AgentCredentials)
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
                "CRM": "Ringy",
                "credentials": {
                    "id_token": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"]
            }
        }
    )


class UpdateAgentModel(BaseModel):
    """
    A set of optional updates to be made to a Agent document in the database.
    """
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    states_with_license: Optional[List] = None
    CRM: Optional[PyObjectId] = Field(default=None)
    creation_time: Optional[datetime.datetime] = None
    campaigns: Optional[List[PyObjectId]] = None
    credentials: Optional[AgentCredentials] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": "Ringy",
                "creation_time": "2020-01-01T00:00:00.000Z",
                "credentials": {
                    "id_token": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e", "324sddsds"]
            }
        }
    )


class AgentCollection(BaseModel):
    """
    A container holding a list of `AgentModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    agents: List[AgentModel]
