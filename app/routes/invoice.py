from bson import ObjectId
from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response
from pymongo import ReturnDocument

from app.db import db
from app.models.invoice import InvoiceModel, UpdateInvoiceModel, InvoiceCollection


router = APIRouter(prefix="/api/invoice", tags=["invoice"])
invoice_collection = db["invoice"]


@router.post(
    "/",
    response_description="Add new invoice",
    response_model=InvoiceModel,
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_invoice(invoice: InvoiceModel = Body(...)):
    """
    Insert a new invoice record.

    A unique `id` will be created and provided in the response.
    """
    new_invoice = await invoice_collection.insert_one(
        invoice.model_dump(by_alias=True, exclude=["id"])
    )
    created_invoice = await invoice_collection.find_one({"_id": new_invoice.inserted_id})
    return created_invoice


@router.get(
    "/",
    response_description="Get all invoices",
    response_model=InvoiceCollection,
    response_model_by_alias=False
)
async def list_invoices(page: int = 1, limit: int = 10):
    """
    List all of the invoice data in the database within the specified page and limit.
    """
    invoices = await invoice_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return InvoiceCollection(invoices=invoices)


@router.get(
    "/{id}",
    response_description="Get a single invoice",
    response_model=InvoiceModel,
    response_model_by_alias=False
)
async def show_invoice(id: str):
    """
    Get the record for a specific invoice, looked up by `id`.
    """
    if (
        invoice := await invoice_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return invoice

    raise HTTPException(status_code=404, detail=f"Invoice {id} not found")


@router.put(
    "/",
    response_description="Update a invoice",
    response_model=InvoiceModel,
    response_model_by_alias=False
)
async def update_invoice(id: str, invoice: UpdateInvoiceModel = Body(...)):
    """
    Update individual fields of an existing invoice record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    invoice = {k: v for k, v in invoice.model_dump(by_alias=True).items() if v is not None}

    if len(invoice) >= 1:
        update_result = await invoice_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": invoice},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise HTTPException(status_code=404, detail=f"Invoice {id} not found")

    if (existing_invoice := await invoice_collection.find_one({"_id": id})) is not None:
        return existing_invoice

    raise HTTPException(status_code=404, detail=f"Invoice {id} not found")


@router.delete("/", response_description="Delete a invoice")
async def delete_invoice(id: str):
    """
    Remove a single invoice record from the database.
    """
    delete_result = await invoice_collection.delete_one({"_id": ObjectId(id)})

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Invoice {id} not found")
