import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import List, Optional, Union

from app.tools.modifiers import PyObjectId


class OrderPriorityDetails(BaseModel):
    """
    A container for order priority details.
    """
    duration: int = Field(default=0)  # in minutes
    start_time: Union[None, datetime.datetime] = Field(None)
    end_time: Union[None, datetime.datetime] = Field(None)
    active: bool = Field(default=False)
    prioritized_by: Union[None, PyObjectId] = Field(None)
    task_id: Union[None, str] = Field(None)


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
    priority: OrderPriorityDetails = Field(default_factory=OrderPriorityDetails)
    past_prioritizations: List[OrderPriorityDetails] = Field(default_factory=list)
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

        def convert_object_ids(item):
            if isinstance(item, dict):
                return {k: convert_object_ids(v) for k, v in item.items()}
            elif isinstance(item, list):
                return [convert_object_ids(v) for v in item]
            elif isinstance(item, ObjectId):
                return str(item)
            else:
                return item

        data = convert_object_ids(data)
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
    priority: OrderPriorityDetails = Optional[OrderPriorityDetails]
    past_prioritizations: List[OrderPriorityDetails] = Optional[List[OrderPriorityDetails]]
    rules: dict = Optional[dict]
    completed_date: Optional[datetime.datetime]


class OrderCollection(BaseModel):
    """
    A container for a collection of order records.
    """
    data: List[OrderModel]
