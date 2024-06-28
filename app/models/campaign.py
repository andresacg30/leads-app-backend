import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import List, Optional, Annotated

PyObjectID = Annotated[str, BeforeValidator(str)]


class CampaignModel(BaseModel):
    """
    Container for a single Campaign record.
    """
    id: Optional[PyObjectID] = Field(alias="_id", default=None)
    name: str = Field(...)
    active: bool = Field(...)
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Campaign 1",
                "active": True
            }
        }
    )


class UpdateCampaignModel(BaseModel):
    """
    A set of optional updates to be made to a Campaign document in the database.
    """
    name: Optional[str] = None
    active: Optional[bool] = None
    start_date: Optional[datetime.datetime] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Campaign 1",
                "active": True,
                "start_date": "2020-01-01T00:00:00.000Z"
            }
        }
    )


class CampaignCollection(BaseModel):
    """
    Container for a list of Campaign records.
    """
    campaigns: List[CampaignModel]
