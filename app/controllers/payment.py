import bson
import difflib

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.models.payment import PaymentModel, UpdatePaymentModel


def get_payment_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["payment"]


class PaymentNotFoundError(Exception):
    pass


class PaymentIdInvalidError(Exception):
    pass


async def get_payment_by_field(**kwargs):
    payment_collection = get_payment_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}

    if "full_name" in query:
        full_name = query.pop("full_name")
        first_name = full_name.split(' ')[0]
        last_name = " ".join(full_name.split(' ')[1:])
        payment = await payment_collection.find_one({"first_name": first_name, "last_name": last_name})
        if payment is None:
            payments = await payment_collection.find().to_list(None)
            full_names = [f"{a['first_name']} {a['last_name']}" for a in payments]
            closest_match = difflib.get_close_matches(full_name, full_names, n=1)
            if closest_match:
                first_name = closest_match[0].split(' ')[0]
                last_name = " ".join(closest_match[0].split(' ')[1:])
                payment = await payment_collection.find_one({"first_name": first_name, "last_name": last_name})
                if not payment:
                    raise PaymentNotFoundError(f"Payment with full name {full_name} not found")
                return payment
            else:
                # send notification
                raise PaymentNotFoundError(f"No close match for payment with full name {full_name}")
        return payment

    payment = await payment_collection.find_one(query)

    if not payment:
        raise PaymentNotFoundError("Payment not found with the provided information.")

    return payment


async def get_enrolled_campaigns(payment_id):
    payment_collection = get_payment_collection()
    try:
        payment = await payment_collection.find_one({"_id": ObjectId(payment_id)})
        enrolled_campaigns = payment['campaigns']
        return enrolled_campaigns
    except bson.errors.InvalidId:
        raise PaymentIdInvalidError(f"Invalid id {payment_id} on get enrolled campaigns function / create payment route.")


async def update_campaigns_for_payment(payment_id, campaigns):
    payment_collection = get_payment_collection()
    updated_payment = await payment_collection.update_one(
        {"_id": payment_id}, {"$set": {"campaigns": campaigns}}
    )
    return updated_payment


async def create_payment(payment: PaymentModel):
    payment_collection = get_payment_collection()
    created_payment = await payment_collection.insert_one(
        payment.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    return created_payment


async def get_all_payments(page, limit):
    payment_collection = get_payment_collection()
    payments = await payment_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return payments


async def get_payment(id):
    payment_collection = get_payment_collection()
    try:
        payment_in_db = await payment_collection.find_one({"_id": ObjectId(id)})
        return payment_in_db
    except bson.errors.InvalidId:
        raise PaymentIdInvalidError(f"Invalid id {id} on get payment route.")


async def update_payment(id, payment: UpdatePaymentModel):
    payment_collection = get_payment_collection()
    try:
        payment = {k: v for k, v in payment.model_dump(by_alias=True, mode="python").items() if v is not None}

        if len(payment) >= 1:
            update_result = await payment_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": payment},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                return update_result

            else:
                raise PaymentNotFoundError(f"Payment with id {id} not found")

        if (existing_payment := await payment_collection.find_one({"_id": id})) is not None:
            return existing_payment
    except bson.errors.InvalidId:
        raise PaymentIdInvalidError(f"Invalid id {id} on update payment route.")


async def delete_payment(id):
    payment_collection = get_payment_collection()
    try:
        result = await payment_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise PaymentIdInvalidError(f"Invalid id {id} on delete payment route.")
