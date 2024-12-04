import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr, ConfigDict, root_validator
from typing import Optional, List, Dict

from app.tools.modifiers import PyObjectId


class UserModel(BaseModel):
    """
    Container for a single User record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    region: str = Field(...)
    phone: str = Field(default=None)
    agent_id: Optional[PyObjectId] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)
    permissions: Optional[list[str]] = Field(default=None)
    campaigns: Optional[list[PyObjectId]] = Field(default=None)
    stripe_customer_ids: Optional[Dict[PyObjectId, str]] = Field(default={})
    balance: Optional[float] = Field(default=0)
    email_verified: bool = Field(default=False)
    account_creation_task_id: Optional[str] = Field(default=None)
    otp_code: Optional[str] = Field(default=None)
    otp_expiration: Optional[datetime.datetime] = Field(default=None)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "janedoe@email.com",
                "password": "password",
                "region": "USA/Eastern",
                "agent_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "permissions": ["user"],
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"]
            }
        }
    )

    @property
    def ROLE_AGENCY(self) -> str:
        return "agency"

    @property
    def ROLE_AGENT(self) -> str:
        return "agent"

    @property
    def ROLE_ADMIN(self) -> str:
        return "admin"

    @property
    def ROLE_NEW_USER(self) -> str:
        return "new_user"

    def is_admin(self) -> bool:
        return self.ROLE_ADMIN in self.permissions

    def is_agent(self) -> bool:
        return self.ROLE_AGENT in self.permissions

    def is_agency(self) -> bool:
        return self.ROLE_AGENCY in self.permissions

    def is_new_user(self) -> bool:
        return self.ROLE_NEW_USER in self.permissions

    def is_email_verified(self) -> bool:
        return self.email_verified

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data

    @root_validator(pre=True)
    def strip_fields(cls, values):
        fields_to_strip = ['first_name', 'last_name', 'phone', 'email']
        for field in fields_to_strip:
            if field in values and isinstance(values[field], str):
                values[field] = values[field].strip()
        return values


class UserSignIn(BaseModel):
    username: str
    password: str
    otp: Optional[str] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "username": "janedoe@email.com",
                "password": "password"
            }
        }
    )


class UserData(BaseModel):
    name: str
    email: EmailStr
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "janedoe@email.com"
            }
        }
    )


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    """
    Container for a single User record without sensitive data.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    email: EmailStr
    region: str
    phone: str
    agent_id: Optional[PyObjectId]
    balance: float
    permissions: list[str]
    campaigns: list[PyObjectId]
    email_verified: bool

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data


class UserCollection(BaseModel):
    """
    Container for a list of User records.
    """
    data: List[UserResponse]
