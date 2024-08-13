from fastapi import APIRouter, Body, status, HTTPException
from fastapi.responses import Response

import app.controllers.invoice as invoice_controller

from app.models.invoice import InvoiceModel, UpdateInvoiceModel, InvoiceCollection


router = APIRouter(prefix="/api/invoice", tags=["invoice"])


@router.post(
    "/",
    response_description="Add new invoice",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_invoice(invoice: InvoiceModel = Body(...)):
    """
    Insert a new invoice record.

    A unique `id` will be created and provided in the response.
    """
    new_invoice = await invoice_controller.create_invoice(invoice)
    return {"id": str(new_invoice.inserted_id)}


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
    invoices = await invoice_controller.get_all_invoices(page=page, limit=limit)
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
    try:
        invoice = await invoice_controller.get_one_invoice(id)
        return invoice

    except invoice_controller.InvoiceNotFoundError:
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
    try:
        updated_invoice = await invoice_controller.update_invoice(id, invoice)
        return {"id": str(updated_invoice["_id"])}

    except invoice_controller.InvoiceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except invoice_controller.InvoiceIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/", response_description="Delete a invoice")
async def delete_invoice(id: str):
    """
    Remove a single invoice record from the database.
    """
    delete_result = await invoice_controller.delete_invoice(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Invoice {id} not found")
