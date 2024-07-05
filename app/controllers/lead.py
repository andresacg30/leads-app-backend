import bson
import datetime

from bson import ObjectId
from pymongo import ReturnDocument

from app.db import db
from app.controllers import agent as agent_controller
from app.models import lead
from app.tools import formatters as formatter


lead_collection = db["lead"]


class LeadNotFoundError(Exception):
    pass


class LeadIdInvalidError(Exception):
    pass


async def update_lead(id, lead):
    try:
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
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on update lead route")


async def update_lead_from_ghl(id, lead):
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True).items() if v is not None}
        if "created_time" in lead:
            lead["created_time"] = formatter.format_time(lead["created_time"])
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
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on update lead route")


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


async def create_lead(lead: lead.LeadModel):
    new_lead = await lead_collection.insert_one(
        lead.model_dump(by_alias=True, exclude=["id"])
    )
    return new_lead


async def get_all_leads(page, limit):
    leads = await lead_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return leads


async def get_one_lead(id):
    try:
        if (
            lead := await lead_collection.find_one({"_id": ObjectId(id)})
        ) is not None:
            return lead

        raise LeadNotFoundError(f"Lead with id {id} not found")
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on lead get one route")


async def delete_lead(id):
    try:
        delete_result = await lead_collection.delete_one({"_id": ObjectId(id)})
        return delete_result
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on delete lead route")


async def update_invalid_lead(lead_id):
    try:
        update_result = await lead_collection.find_one_and_update(
            {"_id": ObjectId(lead_id)},
            {"$set": {"custom_fields.invalid": "yes"}},
            return_document=ReturnDocument.AFTER,
        )
        if update_result is not None:
            return update_result
        else:
            raise LeadNotFoundError(f"Lead with id {lead_id} not found")
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {lead_id} on update invalid lead route")
