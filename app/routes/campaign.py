import ast
import bson
from typing import List
from fastapi import APIRouter, Body, status, HTTPException, Depends
from fastapi.responses import Response

import app.controllers.campaign as campaign_controller
import app.controllers.user as user_controller
import app.integrations.stripe as stripe_integration

from app.auth.jwt_bearer import get_current_user
from app.models.campaign import CampaignModel, UpdateCampaignModel, CampaignCollection
from app.models.user import UserModel


router = APIRouter(prefix="/api/campaign", tags=["campaign"])


@router.get("/get-stripe-account-status")
async def get_stripe_account_status(user: UserModel = Depends(get_current_user)):
    user_campaign: CampaignModel = await campaign_controller.get_campaign_by_admin_id(user.id)  # any campaign the user has links to the same stripe account.
    is_active = await stripe_integration.get_stripe_account_status(account_id=user_campaign.stripe_account_id)
    if is_active:
        user_campaign.status = "active"
        user.permissions = ["agency_admin"]
        await campaign_controller.update_campaign(user_campaign.id, user_campaign)
        await user_controller.update_user(user)
    return {"is_active": is_active}


@router.get("/refresh-stripe-onboarding-url")
async def refresh_stripe_onboarding_url(user: UserModel = Depends(get_current_user)):
    user_campaign: CampaignModel = await campaign_controller.get_campaign_by_admin_id(bson.ObjectId(user.id))
    if not user_campaign:
        raise HTTPException(status_code=404, detail="User does not have admin access to this campaign")
    stripe_onboarding_url = await stripe_integration.refresh_stripe_account_onboarding_url(user_campaign.stripe_account_id)
    user_campaign.stripe_account_onboarding_url = stripe_onboarding_url
    await campaign_controller.update_campaign(user_campaign.id, user_campaign)
    return {"url": stripe_onboarding_url}


@router.get(
    "/get-stripe-onboarding-url",
    response_description="Get stripe onboarding url",
)
async def get_stripe_onboarding_url(user: UserModel = Depends(get_current_user)):
    """
    Get the stripe onboarding url for the user.
    """
    if user.is_agent():
        raise HTTPException(status_code=404, detail="User do not have permission to this action")
    stripe_account_onboarding_url = await campaign_controller.get_stripe_onboarding_url(user.campaigns[0])  # any campaign the user has will return the same onboarding link.
    return {"url": stripe_account_onboarding_url}


@router.post(
    "/get-many",
    response_description="Get multiple campaigns",
    response_model_by_alias=False
)
async def get_multiple_campaigns(ids: List[str] = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Get the record for multiple campaigns, looked up by `ids`.
    """
    try:
        campaigns = await campaign_controller.get_campaigns(ids)
        return {"data": list(campaign.to_json() for campaign in CampaignCollection(data=campaigns).data)}
    except campaign_controller.CampaignNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{id}",
    response_description="Get a single campaign",
    response_model_by_alias=False
)
async def show_campaign(id: str, user: UserModel = Depends(get_current_user)):
    """
    Get the record for a specific campaign, looked up by `id`.
    """
    try:
        if not user.is_admin():
            if not user.campaigns or bson.ObjectId(id) not in user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
        campaign = await campaign_controller.get_one_campaign(id)
        return campaign.to_json()

    except campaign_controller.CampaignNotFoundError:
        raise HTTPException(status_code=404, detail=f"Campaign {id} not found")


@router.put(
    "/{id}",
    response_description="Update a campaign",
    response_model_by_alias=False
)
async def update_campaign(id: str, campaign: UpdateCampaignModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Update individual fields of an existing campaign record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    _is_agent_check(user)
    try:
        updated_campaign = await campaign_controller.update_campaign(id, campaign)
        return {"id": str(updated_campaign["_id"])}

    except campaign_controller.CampaignNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except campaign_controller.CampaignIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a campaign")
async def delete_campaign(id: str, user: UserModel = Depends(get_current_user)):
    """
    Remove a single campaign record from the database.
    """
    if not user.is_admin():
        raise HTTPException(status_code=404, detail="User do not have permission to this action")
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
    "",
    response_description="Add new campaign",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_campaign(campaign: CampaignModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Insert a new campaign record.

    A unique `id` will be created and provided in the response.
    """
    _is_agent_check(user)
    campaign_name = campaign.name
    if await campaign_controller.get_campaign_by_name(campaign_name):
        raise HTTPException(status_code=400, detail=f"Campaign {campaign_name} already exists")
    new_campaign = await campaign_controller.create_campaign(campaign)
    if user.is_agency():
        user.campaigns.append(new_campaign.inserted_id)
        await user_controller.update_user(user)
    return {"id": str(new_campaign.inserted_id)}


@router.get(
    "",
    response_description="Get all campaigns",
    response_model_by_alias=False
)
async def list_campaigns(page: int = 1, limit: int = 10, sort: str = "start_date=DESC" , filter: str = None, user: UserModel = Depends(get_current_user)):
    """
    List all of the campaign data in the database within the specified page and limit.
    """
    if sort.split('=')[1] not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")
    try:
        filter = ast.literal_eval(filter) if filter else None
        if not user.is_admin():
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
            filter["_id"] = {"$in": [bson.ObjectId(campaign_id) for campaign_id in user.campaigns]}
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        campaigns, total = await campaign_controller.get_all_campaigns(page=page, limit=limit, sort=sort, filter=filter)
        return {
            "data": list(campaign.to_json() for campaign in CampaignCollection(data=campaigns).data),
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _is_agent_check(user: UserModel):
    if user.is_agent():
        raise HTTPException(status_code=404, detail="User do not have permission to this action")
