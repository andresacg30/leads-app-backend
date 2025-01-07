import datetime
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union

from app.tools.modifiers import PyObjectId


class TransactionModel(BaseModel):
    """
    A container for a single transaction record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    amount: float = Field(...)
    date: datetime.datetime = Field(...)
    type: str = Field(...)
    user_id: PyObjectId = Field(...)
    description: str = Field(default=None)
    notes: str = Field(default=None)
    campaign_id: Optional[PyObjectId] = Field(default=None)
    lead_id: Optional[Union[PyObjectId, List[PyObjectId]]] = Field(default=None)
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "amount": 100.00,
                "date": "2020-01-01T00:00:00.000Z",
                "transaction_type": "debit",
                "user_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "description": "fresh_lead",
                "notes": "This is a note.",
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


class UpdateTransactionModel(BaseModel):
    """
    A set of optional updates to be made to an transaction document in the database.
    """
    amount: Optional[float] = None
    date: Optional[datetime.datetime] = None
    transaction_type: Optional[str] = None
    user_id: Optional[PyObjectId] = None
    product_description: Optional[str] = None
    notes: Optional[str] = None
    lead_id: Optional[Union[PyObjectId, List[PyObjectId]]] = None
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "amount": 100.00,
                "date": "2020-01-01T00:00:00.000Z",
                "transaction_type": "debit",
                "user_id": "5f9c0a9e9c6d4b1e9c6d4b1e",
                "product_description": "fresh_lead",
                "notes": "This is a note.",
            }
        }
    )


class TransactionCollection(BaseModel):
    """
    A container for a collection of transaction records.
    """
    transactions: List[TransactionModel]
