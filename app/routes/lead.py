import bson
import json

from fastapi import APIRouter, Body, status, HTTPException, Depends
from fastapi.responses import Response
from typing import Optional, Dict, List

import app.controllers.lead as lead_controller

from app.auth.jwt_bearer import get_current_user
from app.background_jobs import lead as lead_background_jobs
from app.models.lead import LeadModel, UpdateLeadModel, LeadCollection
from app.models.user import UserModel
from app.tools import mappings, formatters


router = APIRouter(prefix="/api/lead", tags=["lead"])


@router.post(
    "/mark-as-sold-by-agent",
    response_description="Mark leads as sold by agent",
    response_model_by_alias=False
)
async def mark_leads_as_sold_by_agent(
    lead_ids: List[str] = Body(..., embed=True),
    user: UserModel = Depends(get_current_user)
):
    """
    Mark leads as sold by agent
    """
    if not user.is_agent():
        raise HTTPException(status_code=404, detail="User does not have required permissions")
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Lead ids are required")
    await lead_controller.mark_leads_as_sold(lead_ids)
    return {"message": "Leads marked as sold"}


@router.post(
    "/send-leads-to-agent",
    response_description="Send leads to agent",
    response_model_by_alias=False
)
async def send_leads_to_agent(
    lead_ids: List[str] = Body(...),
    agent_id: str = Body(...),
    campaign_id: str = Body(...),
    user: UserModel = Depends(get_current_user)
):
    """
    Send leads to agent
    """
    if user.is_agent():
        raise HTTPException(status_code=404, detail="User does not have required permissions")
    if not lead_ids:
        raise HTTPException(status_code=400, detail="Lead ids are required")
    if not agent_id:
        raise HTTPException(status_code=400, detail="Agent id is required")
    if agent_id == "null":
        agent_id = None
    lead_background_jobs.send_leads_to_agent(lead_ids, agent_id, campaign_id)
    return {"message": "Leads queued for sending"}


@router.post(
    "/get-many",
    response_description="Get multiple leads",
    response_model_by_alias=False
)
async def get_multiple_leads(ids: List[str] = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Get the record for multiple leads, looked up by `ids`.
    """
    try:
        leads = await lead_controller.get_leads(ids=ids, user=user)
        return {"data": list(lead.to_json() for lead in LeadCollection(data=leads).data)}
    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/find",
    response_description="Search lead id by email and/or buyer name",
    response_model_by_alias=False
)
async def find_leads(
    email: str,
    buyer_name: str = None,
    second_chance_buyer_name: str = None,
    campaign_id: str = None,
    user: UserModel = Depends(get_current_user)
):
    """
    Search for leads by email and/or buyer name.
    """
    try:
        if not user.is_admin():
            if campaign_id and campaign_id not in user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
        if email:
            email = email.lower()
        lead = await lead_controller.get_lead_by_field(
            email=email,
            buyer_name=buyer_name,
            second_chance_buyer_name=second_chance_buyer_name,
            campaign_id=bson.ObjectId(campaign_id)
        )
        return {"id": str(lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/ghl/{id}",
    response_description="Update a lead",
    response_model_by_alias=False
)
async def update_lead_from_ghl(id: str, lead: UpdateLeadModel = Body(...)):
    """
    Update individual fields of an existing lead record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """

    try:
        if lead.email:
            lead.email = lead.email.lower()
        updated_lead = await lead_controller.update_lead_from_ghl(id, lead)
        return {"id": str(updated_lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except lead_controller.LeadIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except lead_controller.LeadEmptyError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{id}",
    response_description="Get a single lead",
    response_model_by_alias=False
)
async def show_lead(id: str, user: UserModel = Depends(get_current_user)):
    """
    Get the record for a specific lead, looked up by `id`.
    """
    try:
        lead = await lead_controller.get_one_lead(id)
        if not user.is_admin():
            if lead.campaign_id not in user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
            if user.is_agent():
                if lead.buyer_id != user.agent_id:
                    raise HTTPException(status_code=404, detail="User does not have access to this lead")
                if lead.custom_fields.get("invalid"):
                    del lead.custom_fields["invalid"]
                if lead.custom_fields.get("invalid_reason"):
                    del lead.custom_fields["invalid_reason"]
                if lead.custom_fields.get("trustedform_url"):
                    del lead.custom_fields["trustedform_url"]
        return lead.to_json()

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/{id}",
    response_description="Update a lead",
    response_model_by_alias=False
)
async def update_lead(id: str, lead: UpdateLeadModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Update individual fields of an existing lead record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """

    try:
        if not user.is_admin():
            raise HTTPException(status_code=404, detail="User does not have required permissions")
        if lead.email:
            lead.email = lead.email.lower()
        updated_lead = await lead_controller.update_lead(id, lead)
        return {"id": str(updated_lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except lead_controller.LeadIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except lead_controller.LeadEmptyError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a lead")
async def delete_lead(id: str, user: UserModel = Depends(get_current_user)):
    """
    Remove a single lead record from the database.
    """
    if not user.is_admin():
        raise HTTPException(status_code=404, detail="User does not have required permissions")
    if len(id.split(",")) > 1:
        id = id.split(",")
        delete_result = await lead_controller.delete_leads(ids=id)
        if delete_result.deleted_count >= 1:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
    delete_result = await lead_controller.delete_lead(id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Lead {id} not found")


@router.post(
    "",
    response_description="Add new lead",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_lead(lead: LeadModel = Body(...), user: UserModel = Depends(get_current_user)):
    """
    Insert a new lead record.

    A unique `id` will be created and provided in the response.
    """
    if not user.is_admin():
        raise HTTPException(status_code=404, detail="User can't create leads")
    for state, state_variations in mappings.state_mappings.items():
        if lead.state.lower() in state_variations:
            lead.state = state
            break
    else:
        raise HTTPException(status_code=400, detail=f"Invalid state {lead.state}")
    lead.email = lead.email.lower()
    new_lead = await lead_controller.create_lead(lead)
    return {"id": str(new_lead.inserted_id)}


@router.get(
    "",
    response_description="Get all leads",
    response_model_by_alias=False
)
async def list_leads(page: int = 1, limit: int = 10, sort: str = "created_time=DESC", filter: str = None, user: UserModel = Depends(get_current_user)):
    """
    List all of the lead data in the database within the specified page and limit.
    """
    try:
        filter = _parse_filter(filter)
        if filter:
            filter = _handle_buyer_filters(filter)
            if "state" in filter:
                filter = _handle_state_filters(filter)
        sort = _build_sort_tuple(sort)
        filter = _handle_user_filters(filter, user)

        leads, total = await lead_controller.get_all_leads(page=page, limit=limit, sort=sort, filter=filter)
        return {"data": list(lead.to_json() for lead in LeadCollection(data=leads).data), "total": total}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _parse_filter(filter_str: Optional[str]) -> Optional[Dict]:
    if filter_str:
        try:
            return json.loads(filter_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid filter string: {e}")
    return None


def _handle_state_filters(filter: Dict) -> Dict:
    if "state" in filter:
        states = filter["state"]
        state_abbr_list = [formatters.get_full_state_name(state) for state in states]
        filter["state"] = {"$in": state_abbr_list}
    return filter


def _build_sort_tuple(sort_str: str) -> tuple:
    sort_field, sort_order = sort_str.split('=')
    return (sort_field, 1 if sort_order == "ASC" else -1)


def _handle_user_filters(filter: Dict, user: UserModel) -> Dict:
    if not user.is_admin():
        if not filter:
            filter = {}
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this campaign")
        if "campaign_id" not in filter:
            user.campaigns = [bson.ObjectId(campaign_id) for campaign_id in user.campaigns]
            filter["campaign_id"] = {"$in": user.campaigns}
        else:
            filter["campaign_id"] = bson.ObjectId(filter["campaign_id"])
            if filter["campaign_id"] not in user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
        if user.is_agent():
            filter["$or"] = [
                {"buyer_id": user.agent_id},
                {"second_chance_buyer_id": user.agent_id}
            ]
            filter["agent_id"] = user.agent_id
    else:
        if "campaign_id" in filter:
            filter["campaign_id"] = bson.ObjectId(filter["campaign_id"])
    return filter


def _handle_buyer_filters(filter: Dict) -> Dict:
    if "buyer_id" in filter and "null" in filter["buyer_id"]:
        filter["buyer_id"] = None
        filter["$or"] = [{"custom_fields.invalid": "no"}, {"custom_fields.invalid": {"$exists": False}}]
    if "second_chance_buyer_id" in filter and "null" in filter["second_chance_buyer_id"]:
        filter["second_chance_buyer_id"] = None
        filter["$or"] = [{"custom_fields.invalid": "no"}, {"custom_fields.invalid": {"$exists": False}}]
    return filter
