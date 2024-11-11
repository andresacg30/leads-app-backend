import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

from app.tools.modifiers import PyObjectId


class CampaignModel(BaseModel):
    """
    Container for a single Campaign record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str = Field(...)
    active: bool = Field(...)
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    sign_up_code: Optional[str] = Field(default=None)
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

    def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        return data


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
    data: List[CampaignModel]
