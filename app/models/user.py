from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import Optional, Annotated


PyObjectId = Annotated[str, BeforeValidator(str)]


class UserModel(BaseModel):
    """
    Container for a single User record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    first_name: str = Field(...)
    last_name: str = Field(...)
    email: EmailStr = Field(...)
    password: str = Field(...)
    region: str = Field(...)
    agent_id: Optional[PyObjectId] = Field(default=None)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedoe@email.com",
                "password": "password",
                "region": "USA/Eastern",
                "agent_id": "5f9c0a9e9c6d4b1e9c6d4b1e"
            }
        }
    )

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


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
    full_name: str
    email: EmailStr
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "full_name": "Jane Doe",
                "email": "janedoe@email.com"
            }
        }
    )