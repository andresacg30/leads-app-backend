from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response

import app.controllers.lead as lead_controller

from app.db import db
from app.models.lead import LeadModel, UpdateLeadModel, LeadCollection, UpdateInvalidLeadModel
from app.tools import mappings


router = APIRouter(prefix="/api/lead", tags=["lead"])
lead_collection = db["lead"]


@router.post(
    "/",
    response_description="Add new lead",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_lead(lead: LeadModel = Body(...)):
    """
    Insert a new lead record.

    A unique `id` will be created and provided in the response.
    """
    for state, state_variations in mappings.state_mappings.items():
        if lead.state.lower() in state_variations:
            lead.state = state
            break
    new_lead = await lead_controller.create_lead(lead)
    return {"id": str(new_lead.inserted_id)}


@router.get(
    "/",
    response_description="Get all leads",
    response_model=LeadCollection,
    response_model_by_alias=False
)
async def list_leads(page: int = 1, limit: int = 10):
    """
    List all of the lead data in the database within the specified page and limit.
    """
    leads = await lead_controller.get_all_leads(page=page, limit=limit)
    return LeadCollection(leads=leads)


@router.get(
    "/{id}",
    response_description="Get a single lead",
    response_model=LeadModel,
    response_model_by_alias=False
)
async def show_lead(id: str):
    """
    Get the record for a specific lead, looked up by `id`.
    """
    try:
        lead = await lead_controller.get_one_lead(id)
        return lead

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/",
    response_description="Update a lead",
    response_model_by_alias=False
)
async def update_lead(id: str, lead: UpdateLeadModel = Body(...)):
    """
    Update individual fields of an existing lead record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """

    try:
        updated_lead = await lead_controller.update_lead(id, lead)
        return {"id": str(updated_lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except lead_controller.LeadIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/", response_description="Delete a lead")
async def delete_lead(id: str):
    """
    Remove a single lead record from the database.
    """
    delete_result = await lead_controller.delete_lead(id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Lead {id} not found")


@router.get(
    "/find/",
    response_description="Search lead id by email and/or buyer name",
    response_model_by_alias=False
)
async def find_leads(
    email: str, buyer_name: str = None, campaign_id: str = None
):
    """
    Search for leads by email and/or buyer name.
    """
    try:
        lead = await lead_controller.get_lead_by_field(email=email, buyer_name=buyer_name, campaign_id=campaign_id)
        return {"id": str(lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put(
    "/ghl",
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
        updated_lead = await lead_controller.update_lead_from_ghl(id, lead)
        return {"id": str(updated_lead["_id"])}

    except lead_controller.LeadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except lead_controller.LeadIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))
