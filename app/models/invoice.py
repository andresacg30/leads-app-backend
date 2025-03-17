from datetime import datetime
from enum import Enum
from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field

from app.tools.modifiers import PyObjectId


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELED = "canceled"


class LeadDistributionTier(BaseModel):
    tier_name: str
    start_count: int
    end_count: Optional[int] = None
    price_per_lead: float


class InvoiceItemModel(BaseModel):
    lead_type: str
    count: int
    amount: float
    tiers: List[dict] = Field(default_factory=list)


class InvoiceModel(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    campaign_id: PyObjectId
    admin_id: PyObjectId
    start_date: datetime
    end_date: datetime
    items: List[InvoiceItemModel] = Field(default_factory=list)
    total_amount: float = 0
    status: InvoiceStatus = InvoiceStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    stripe_invoice_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def to_json(self):
        return {
            "id": str(self.id),
            "campaign_id": str(self.campaign_id),
            "admin_id": str(self.admin_id),
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "items": [item.dict() for item in self.items],
            "total_amount": self.total_amount,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "stripe_invoice_id": self.stripe_invoice_id
        }
