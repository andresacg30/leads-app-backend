from typing import List
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response

import app.controllers.campaign as campaign_controller
import ast

from app.models.campaign import CampaignModel, UpdateCampaignModel, CampaignCollection


router = APIRouter(prefix="/api/campaign", tags=["campaign"])


@router.post(
    "/",
    response_description="Add new campaign",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_campaign(campaign: CampaignModel = Body(...)):
    """
    Insert a new campaign record.

    A unique `id` will be created and provided in the response.
    """
    campaign_name = campaign.name
    if await campaign_controller.get_campaign_by_name(campaign_name):
        raise HTTPException(status_code=400, detail=f"Campaign {campaign_name} already exists")
    new_campaign = await campaign_controller.create_campaign(campaign)
    return {"id": str(new_campaign.inserted_id)}


@router.get(
    "/",
    response_description="Get all campaigns",
    response_model=CampaignCollection,
    response_model_by_alias=False
)
async def list_campaigns(page: int = 1, limit: int = 10, sort: str = "start_date=1" , filter: str = None):
    """
    List all of the campaign data in the database within the specified page and limit.
    """
    if sort.split('=')[1] not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")
    try:
        filter = ast.literal_eval(filter) if filter else None
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        campaigns, total = await campaign_controller.get_all_campaigns(page=page, limit=limit, sort=sort, filter=filter)
        return {
            "data": list(campaign.model_dump() for campaign in CampaignCollection(data=campaigns).data),
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{id}",
    response_description="Get a single campaign",
    response_model=CampaignModel,
    response_model_by_alias=False
)
async def show_campaign(id: str):
    """
    Get the record for a specific campaign, looked up by `id`.
    """
    try:
        campaign = await campaign_controller.get_one_campaign(id)
        return campaign

    except campaign_controller.CampaignNotFoundError:
        raise HTTPException(status_code=404, detail=f"Campaign {id} not found")


@router.put(
    "/{id}",
    response_description="Update a campaign",
    response_model_by_alias=False
)
async def update_campaign(id: str, campaign: UpdateCampaignModel = Body(...)):
    """
    Update individual fields of an existing campaign record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    try:
        updated_campaign = await campaign_controller.update_campaign(id, campaign)
        return {"id": str(updated_campaign["_id"])}

    except campaign_controller.CampaignNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except campaign_controller.CampaignIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a campaign")
async def delete_campaign(id: str):
    """
    Remove a single campaign record from the database.
    """
    if len(id.split(",")) > 1:
        id = id.split(",")
        delete_result = await campaign_controller.delete_campaigns(ids=id)
        if delete_result.deleted_count >= 1:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    delete_result = await campaign_controller.delete_campaign(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Campaign {id} not found")


@router.post(
    "/get-many",
    response_description="Get multiple campaigns",
    response_model_by_alias=False
)
async def get_multiple_campaigns(ids: List[str] = Body(...)):
    """
    Get the record for multiple campaigns, looked up by `ids`.
    """
    try:
        campaigns = await campaign_controller.get_campaigns(ids)
        return {"data": list(campaign.model_dump() for campaign in CampaignCollection(data=campaigns).data)}
    except campaign_controller.CampaignNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
