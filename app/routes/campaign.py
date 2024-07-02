from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

import app.controllers.campaign as campaign_controller

from app.db import db
from app.models.campaign import CampaignModel, UpdateCampaignModel, CampaignCollection


router = APIRouter(prefix="/api/campaign", tags=["campaign"])
campaign_collection = db["campaign"]


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
    new_campaign = await campaign_controller.create_campaign(campaign)
    return {"id": str(new_campaign.inserted_id)}


@router.get(
    "/",
    response_description="Get all campaigns",
    response_model=CampaignCollection,
    response_model_by_alias=False
)
async def list_campaigns(page: int = 1, limit: int = 10):
    """
    List all of the campaign data in the database within the specified page and limit.
    """
    campaigns = await campaign_controller.get_campaigns(page=page, limit=limit)
    return CampaignCollection(campaigns=campaigns)


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

    except campaign_controller.CampaignNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Campaign {id} not found")


@router.put(
    "/",
    response_description="Update a campaign",
    response_model=CampaignModel,
    response_model_by_alias=False
)
async def update_campaign(id: str, campaign: UpdateCampaignModel = Body(...)):
    """
    Update individual fields of an existing campaign record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    campaign = {k: v for k, v in campaign.model_dump(by_alias=True).items() if v is not None}

    if len(campaign) >= 1:
        update_result = await campaign_controller.update_campaign(id=id, campaign=campaign)

        if update_result is not None:
            return update_result

        else:
            raise HTTPException(status_code=404, detail=f"Campaign {id} not found")

    if (existing_campaign := await campaign_collection.find_one({"_id": id})) is not None:
        return existing_campaign

    raise HTTPException(status_code=404, detail=f"Campaign {id} not found")


@router.delete("/", response_description="Delete a campaign")
async def delete_campaign(id: str):
    """
    Remove a single campaign record from the database.
    """
    delete_result = await campaign_controller.delete_campaign(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Campaign {id} not found")
