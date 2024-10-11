from bson import ObjectId
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional

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
    agent_id: Optional[PyObjectId] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)
    permissions: Optional[list[str]] = Field(default=None)
    campaigns: Optional[list[PyObjectId]] = Field(default=None)
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

    def is_admin(self) -> bool:
        return self.ROLE_ADMIN in self.permissions

    def is_agent(self) -> bool:
        return self.ROLE_AGENT in self.permissions

    def is_agency(self) -> bool:
        return self.ROLE_AGENCY in self.permissions

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data


class UserSignIn(HTTPBasicCredentials):
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
