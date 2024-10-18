import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

from app.tools.modifiers import PyObjectId


class PaymentTypeRequest(BaseModel):
    payment_type: str


class ProductSelection(BaseModel):
    product_id: str
    quantity: int = 1  # Default quantity is 1


class CheckoutRequest(BaseModel):
    payment_type: str  # "one_time" or "recurring"
    products: List[ProductSelection]


class PaymentModel(BaseModel):
    """
    A container for a single payment record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    amount: float = Field(...)
    created_time: datetime.datetime = Field(...)
    user_id: PyObjectId = Field(...)
    notes: str = Field(default=None)
    paid: bool = Field(default=False)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "amount": 100.00,
                "created_time": "2020-01-01T00:00:00.000Z",
                "agent_id": 1,
                "notes": "This is a note.",
                "paid": False
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


class UpdatePaymentModel(BaseModel):
    """
    A set of optional updates to be made to an payment document in the database.
    """
    amount: Optional[float] = None
    created_time: Optional[datetime.datetime] = None
    agent_id: Optional[int] = None
    notes: Optional[str] = None
    paid: Optional[bool] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "amount": 100.00,
                "created_time": "2020-01-01T00:00:00.000Z",
                "agent_id": 1,
                "notes": "This is a note.",
                "paid": False
            }
        }
    )


class PaymentCollection(BaseModel):
    """
    A container for a collection of payment records.
    """
    payments: List[PaymentModel]
