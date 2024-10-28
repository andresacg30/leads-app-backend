import bson

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
