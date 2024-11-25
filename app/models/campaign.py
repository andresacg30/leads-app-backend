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
    status: str = Field(default="oboarding")
    start_date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    sign_up_code: Optional[str] = Field(default=None)
    stripe_account_id: Optional[str] = Field(default=None)
    stripe_account_onboarding_url: Optional[str] = Field(default=None)
    admin_id: PyObjectId = Field(default=None)
    price_per_lead: Optional[float] = Field(default=None)
    price_per_second_chance_lead: Optional[float] = Field(default=None)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "name": "Campaign 1",
                "status": "active",
                "start_date": "2020-01-01T00:00:00.000Z",
                "sign_up_code": "abc123",
                "admins": "5f0c3e6f8b3b1f5b6f3a9b4b",
                "price_per_lead": 5.00,
                "price_per_second_chance_lead": 2.50
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
    status: Optional[str] = None
    start_date: Optional[datetime.datetime] = None
    sign_up_code: Optional[str] = None
    stripe_account_id: Optional[str] = None
    stripe_account_onboarding_url: Optional[str] = None
    admin_id: Optional[PyObjectId] = None
    price_per_lead: Optional[float] = None
    price_per_second_chance_lead: Optional[float] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "name": "Campaign 1",
                "status": "inactive",
                "start_date": "2020-01-01T00:00:00.000Z",
                "sign_up_code": "abc123",
                "admin_id": "5f0c3e6f8b3b1f5b6f3a9b4b",
                "price_per_lead": 5.00,
                "price_per_second_chance_lead": 2.50
            }
        }
    )


class CampaignCollection(BaseModel):
    """
    Container for a list of Campaign records.
    """
    data: List[CampaignModel]
