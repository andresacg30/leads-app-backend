from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

from app.db import db
from app.models.crm import CRMModel, UpdateCRMModel, CRMCollection


router = APIRouter(prefix="/api/crm", tags=["crm"])
CRM_collection = db["crm"]


@router.post(
    "/",
    response_description="Add new CRM",
    response_model=CRMModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_CRM(CRM: CRMModel = Body(...)):
    """
    Insert a new CRM record.

    A unique `id` will be created and provided in the response.
    """
    new_CRM = await CRM_collection.insert_one(
        CRM.model_dump(by_alias=True, exclude=["id"])
    )
    created_CRM = await CRM_collection.find_one({"_id": new_CRM.inserted_id})
    return created_CRM


@router.get(
    "/",
    response_description="Get all CRMs",
    response_model=CRMCollection,
    response_model_by_alias=False
)
async def list_CRMs(page: int = 1, limit: int = 10):
    """
    List all of the CRM data in the database within the specified page and limit.
    """
    CRMs = await CRM_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return CRMCollection(CRMs=CRMs)


@router.get(
    "/{id}",
    response_description="Get a single CRM",
    response_model=CRMModel,
    response_model_by_alias=False
)
async def show_CRM(id: str):
    """
    Get the record for a specific CRM, looked up by `id`.
    """
    if (
        crm := await CRM_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return crm

    raise HTTPException(status_code=404, detail=f"CRM {id} not found")


@router.put(
    "/",
    response_description="Update a CRM",
    response_model=CRMModel,
    response_model_by_alias=False
)
async def update_CRM(id: str, CRM: UpdateCRMModel = Body(...)):
    """
    Update individual fields of an existing CRM record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    CRM = {k: v for k, v in CRM.model_dump(by_alias=True).items() if v is not None}

    if len(CRM) >= 1:
        update_result = await CRM_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": CRM},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise HTTPException(status_code=404, detail=f"CRM {id} not found")

    if (existing_CRM := await CRM_collection.find_one({"_id": id})) is not None:
        return existing_CRM

    raise HTTPException(status_code=404, detail=f"CRM {id} not found")


@router.delete("/", response_description="Delete a CRM")
async def delete_CRM(id: str):
    """
    Remove a single CRM record from the database.
    """
    delete_result = await CRM_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"CRM {id} not found")
