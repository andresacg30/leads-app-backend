import asyncio
from pydantic import BaseModel
from datetime import datetime
from fastapi import APIRouter, status, HTTPException, Depends

import app.controllers.agent as agent_controller
import app.controllers.lead as lead_controller
import app.controllers.order as order_controller

from app.auth.jwt_bearer import get_current_user
from app.models.user import UserModel


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DateRange(BaseModel):
    start: datetime
    end: datetime


class DateRangesRequest(BaseModel):
    thisWeek: DateRange
    lastWeek: DateRange
    thisMonth: DateRange
    lastMonth: DateRange


@router.post(
    "/metrics",
    status_code=status.HTTP_200_OK
)
async def get_dashboard_metrics(date_ranges: DateRangesRequest, user: UserModel = Depends(get_current_user)):
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized"
        )

    campaigns = user.campaigns
    order_metrics, lead_metrics, agent_metrics = await asyncio.gather(
        order_controller.get_order_metrics(campaigns),
        lead_controller.get_lead_counts(date_ranges.model_dump(), campaigns),
        agent_controller.get_agent_metrics(campaigns)
    )

    return {
        "orders": order_metrics,
        "leads": lead_metrics,
        "agents": agent_metrics
    }


@router.get(
    "/unsold-leads",
    status_code=status.HTTP_200_OK,
)
async def get_unsold_leads(user: UserModel = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    campaigns = user.campaigns
    result = await lead_controller.get_unsold_leads(campaigns=campaigns)
    return result
