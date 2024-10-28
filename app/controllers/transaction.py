import bson
import bson.errors

from bson import ObjectId
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.models.transaction import TransactionModel, UpdateTransactionModel

import app.controllers.user as user_controller


def get_transaction_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["transaction"]


class TransactionNotFoundError(Exception):
    pass


class TransactionIdInvalidError(Exception):
    pass


async def create_transaction(transaction: TransactionModel):
    transaction_collection = get_transaction_collection()
    created_transaction = await transaction_collection.insert_one(
        transaction.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    await user_controller.update_user_balance(transaction.user_id, transaction.amount)
    return created_transaction


async def get_all_transactions(page, limit):
    transaction_collection = get_transaction_collection()
    transactions = await transaction_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return transactions


async def get_transaction(id):
    transaction_collection = get_transaction_collection()
    try:
        transaction_in_db = await transaction_collection.find_one({"_id": ObjectId(id)})
        return transaction_in_db
    except bson.errors.InvalidId:
        raise TransactionIdInvalidError(f"Invalid id {id} on get transaction route.")


async def update_transaction(id, transaction: UpdateTransactionModel):
    transaction_collection = get_transaction_collection()
    try:
        transaction = {k: v for k, v in transaction.model_dump(by_alias=True, mode="python").items() if v is not None}

        if len(transaction) >= 1:
            update_result = await transaction_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": transaction},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                return update_result

            else:
                raise TransactionNotFoundError(f"Transaction with id {id} not found")

        if (existing_transaction := await transaction_collection.find_one({"_id": id})) is not None:
            return existing_transaction
    except bson.errors.InvalidId:
        raise TransactionIdInvalidError(f"Invalid id {id} on update transaction route.")


async def delete_transaction(id):
    transaction_collection = get_transaction_collection()
    try:
        result = await transaction_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise TransactionIdInvalidError(f"Invalid id {id} on delete transaction route.")
