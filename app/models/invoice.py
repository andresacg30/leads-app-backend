import datetime
from pydantic import BaseModel, Field, ConfigDict
from pydantic.functional_validators import BeforeValidator
from typing import List, Optional, Annotated


PyObjectId = Annotated[str, BeforeValidator(str)]


class InvoiceModel(BaseModel):
    """
    A container for a single invoice record.
    """
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    amount: float = Field(...)
    created_time: datetime.datetime = Field(...)
    agent_id: int = Field(...)
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


class UpdateInvoiceModel(BaseModel):
    """
    A set of optional updates to be made to an invoice document in the database.
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


class InvoiceCollection(BaseModel):
    """
    A container for a collection of invoice records.
    """
    invoices: List[InvoiceModel]
