from bson import ObjectId
from pydantic.functional_validators import BeforeValidator
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Annotated, List

PyObjectId = Annotated[str, BeforeValidator(str)]


class CRMModel(BaseModel):
    """
    Container for a single CRM record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    url: str = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Ringy",
                "url": "www.ringy.com"
                }
            }
    )


class UpdateCRMModel(BaseModel):
    """
    A set of optional updates to be made to a Agent document in the database.
    """
    name: str = Field(...)
    url: str = Field(...)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Ringy",
                "url": "www.ringy.com"
                },
            }
    )


class CRMCollection(BaseModel):
    """
    A container holding a list of `CRMModel` instances.

    This exists because providing a top-level array in a JSON response can be a [vulnerability](https://haacked.com/archive/2009/06/25/json-hijacking.aspx/)
    """
    CRMs: List[CRMModel]
