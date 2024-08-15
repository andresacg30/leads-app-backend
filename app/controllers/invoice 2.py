import bson
import difflib

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.models.invoice import InvoiceModel, UpdateInvoiceModel


def get_invoice_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["invoice"]


class InvoiceNotFoundError(Exception):
    pass


class InvoiceIdInvalidError(Exception):
    pass


async def get_invoice_by_field(**kwargs):
    invoice_collection = get_invoice_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}

    if "full_name" in query:
        full_name = query.pop("full_name")
        first_name = full_name.split(' ')[0]
        last_name = " ".join(full_name.split(' ')[1:])
        invoice = await invoice_collection.find_one({"first_name": first_name, "last_name": last_name})
        if invoice is None:
            invoices = await invoice_collection.find().to_list(None)
            full_names = [f"{a['first_name']} {a['last_name']}" for a in invoices]
            closest_match = difflib.get_close_matches(full_name, full_names, n=1)
            if closest_match:
                first_name = closest_match[0].split(' ')[0]
                last_name = " ".join(closest_match[0].split(' ')[1:])
                invoice = await invoice_collection.find_one({"first_name": first_name, "last_name": last_name})
                if not invoice:
                    raise InvoiceNotFoundError(f"Invoice with full name {full_name} not found")
                return invoice
            else:
                # send notification
                raise InvoiceNotFoundError(f"No close match for invoice with full name {full_name}")
        return invoice

    invoice = await invoice_collection.find_one(query)

    if not invoice:
        raise InvoiceNotFoundError("Invoice not found with the provided information.")

    return invoice


async def get_enrolled_campaigns(invoice_id):
    invoice_collection = get_invoice_collection()
    try:
        invoice = await invoice_collection.find_one({"_id": ObjectId(invoice_id)})
        enrolled_campaigns = invoice['campaigns']
        return enrolled_campaigns
    except bson.errors.InvalidId:
        raise InvoiceIdInvalidError(f"Invalid id {invoice_id} on get enrolled campaigns function / create invoice route.")


async def update_campaigns_for_invoice(invoice_id, campaigns):
    invoice_collection = get_invoice_collection()
    updated_invoice = await invoice_collection.update_one(
        {"_id": invoice_id}, {"$set": {"campaigns": campaigns}}
    )
    return updated_invoice


async def create_invoice(invoice: InvoiceModel):
    invoice_collection = get_invoice_collection()
    created_invoice = await invoice_collection.insert_one(
        invoice.model_dump(by_alias=True, exclude=["id"])
    )
    return created_invoice


async def get_all_invoices(page, limit):
    invoice_collection = get_invoice_collection()
    invoices = await invoice_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return invoices


async def get_invoice(id):
    invoice_collection = get_invoice_collection()
    try:
        invoice_in_db = await invoice_collection.find_one({"_id": ObjectId(id)})
        return invoice_in_db
    except bson.errors.InvalidId:
        raise InvoiceIdInvalidError(f"Invalid id {id} on get invoice route.")


async def update_invoice(id, invoice: UpdateInvoiceModel):
    invoice_collection = get_invoice_collection()
    try:
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
                raise InvoiceNotFoundError(f"Invoice with id {id} not found")

        if (existing_invoice := await invoice_collection.find_one({"_id": id})) is not None:
            return existing_invoice
    except bson.errors.InvalidId:
        raise InvoiceIdInvalidError(f"Invalid id {id} on update invoice route.")


async def delete_invoice(id):
    invoice_collection = get_invoice_collection()
    try:
        result = await invoice_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise InvoiceIdInvalidError(f"Invalid id {id} on delete invoice route.")
