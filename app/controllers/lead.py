import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.db import db


lead_collection = db["lead"]


class LeadNotFoundError(Exception):
    pass


async def update_lead(id, lead):
    lead = {k: v for k, v in lead.model_dump(by_alias=True).items() if v is not None}
    if "buyer_id" in lead:
        lead["lead_sold_time"] = datetime.datetime.utcnow()
    if "second_chance_buyer_id" in lead:
        lead["second_chance_lead_sold_time"] = datetime.datetime.utcnow()
    if len(lead) >= 1:
        update_result = await lead_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": lead},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise LeadNotFoundError(f"Lead with id {id} not found")

    if (existing_lead := await lead_collection.find_one({"_id": id})) is not None:
        return existing_lead
