import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional

from app.tools.modifiers import PyObjectId


class OrderModel(BaseModel):
    """
    A container for a single order record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    date: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    campaign_id: PyObjectId = Field(...)
    status: str = Field(...)
    order_total: float = Field(...)
    type: str = Field(...)
    agent_id: PyObjectId = Field(...)
    fresh_lead_amount: int = Field(default=0)
    second_chance_lead_amount: int = Field(default=0)
    rules: dict = Field(default={})
    completed_date: Optional[datetime.datetime] = Field(default=None)

    @property
    async def fresh_lead_completed(self):
        from app.controllers.order import get_lead_count
        return await get_lead_count(self.id)

    @property
    async def second_chance_lead_completed(self):
        from app.controllers.order import get_second_chance_lead_count
        return await get_second_chance_lead_count(self.id)

    async def to_json(self):
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(value, ObjectId):
                data[key] = str(value)
            elif isinstance(value, list):
                data[key] = [str(v) if isinstance(v, ObjectId) else v for v in value]
        data["fresh_lead_completed"] = await self.fresh_lead_completed
        data["second_chance_lead_completed"] = await self.second_chance_lead_completed
        return data


class UpdateOrderModel(BaseModel):
    """
    A set of optional updates to be made to an order document in the database.
    """
    date: Optional[datetime.datetime]
    agent_id: Optional[PyObjectId]
    campaign_id: Optional[PyObjectId]
    status: Optional[str]
    fresh_lead_completed: Optional[int]
    type: Optional[str]
    fresh_lead_amount: Optional[int]
    second_chance_lead_completed: Optional[int]
    second_chance_lead_amount: Optional[int]
    order_total: int = Optional[int]
    rules: dict = Optional[dict]
    completed_date: Optional[datetime.datetime]


class OrderCollection(BaseModel):
    """
    A container for a collection of order records.
    """
    data: List[OrderModel]
