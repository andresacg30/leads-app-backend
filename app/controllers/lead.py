import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.db import db
from app.controllers import agent as agent_controller


lead_collection = db["lead"]


class LeadNotFoundError(Exception):
    pass


async def update_lead(id, lead):
    lead = {k: v for k, v in lead.model_dump(by_alias=True).items() if v is not None}
    if "buyer_id" in lead:
        lead["lead_sold_time"] = datetime.datetime.utcnow()
    if "second_chance_buyer_id" in lead:
        lead["second_chance_lead_sold_time"] = datetime.datetime.utcnow()
    if "lead_sold_by_agent_time" in lead:
        lead["lead_sold_by_agent_time"] = datetime.datetime.utcnow()
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


async def get_lead_by_field(**kwargs):
    query = {k: v for k, v in kwargs.items() if v is not None}

    if "buyer_name" in query:
        try:
            buyer_id = await agent_controller.get_agent_by_field(full_name=query.pop("buyer_name"))
            query["buyer_id"] = str(buyer_id["_id"])
        except agent_controller.AgentNotFoundError as e:
            raise LeadNotFoundError(str(e))
    lead = await lead_collection.find_one(query)
    if not lead:
        raise LeadNotFoundError("Lead not found with the provided information.")

    return lead
