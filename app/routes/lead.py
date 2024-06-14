from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

from app.db import db
from app.models.lead import LeadModel, UpdateLeadModel, LeadCollection


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
    new_lead = await lead_collection.insert_one(
        lead.model_dump(by_alias=True, exclude=["id"])
    )
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
    leads = await lead_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
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
    if (
        lead := await lead_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return lead

    raise HTTPException(status_code=404, detail=f"Lead {id} not found")


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
    lead = {k: v for k, v in lead.model_dump(by_alias=True).items() if v is not None}

    if len(lead) >= 1:
        update_result = await lead_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": lead},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise HTTPException(status_code=404, detail=f"Lead {id} not found")

    if (existing_lead := await lead_collection.find_one({"_id": id})) is not None:
        return {"id": existing_lead["_id"]}

    raise HTTPException(status_code=404, detail=f"Lead {id} not found")


@router.delete("/", response_description="Delete a lead")
async def delete_lead(id: str):
    """
    Remove a single lead record from the database.
    """
    delete_result = await lead_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Lead {id} not found")
