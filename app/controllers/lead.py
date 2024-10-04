import bson

from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from motor.core import AgnosticCollection


from app.db import Database
from app.controllers import agent as agent_controller
from app.models import lead
from app.tools import formatters as formatter


def get_lead_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["lead"]


class LeadNotFoundError(Exception):
    pass


class LeadIdInvalidError(Exception):
    pass


class LeadEmptyError(Exception):
    pass


async def update_lead(id, lead: lead.UpdateLeadModel):
    if all(v is None for v in lead.model_dump().values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True).items() if v is not None}
        if "buyer_id" in lead:
            lead["lead_sold_time"] = datetime.utcnow()
        if "second_chance_buyer_id" in lead:
            lead["second_chance_lead_sold_time"] = datetime.utcnow()
        if "lead_sold_by_agent_time" in lead:
            lead["lead_sold_by_agent_time"] = datetime.utcnow()
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


async def update_lead_from_ghl(id, lead: lead.UpdateLeadModel):
    if all(v is None for v in lead.model_dump().values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
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
    lead_collection = get_lead_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}
    if "buyer_name" in query:
        try:
            buyer_id = await agent_controller.get_agent_by_field(full_name=query.pop("buyer_name"))
            query["buyer_id"] = str(buyer_id["_id"])
        except agent_controller.AgentNotFoundError as e:
            raise LeadNotFoundError(str(e))
    if "second_chance_buyer_name" in query:
        try:
            second_chance_buyer_id = await agent_controller.get_agent_by_field(full_name=query.pop("second_chance_buyer_name"))
            query["second_chance_buyer_id"] = str(second_chance_buyer_id["_id"])
        except agent_controller.AgentNotFoundError as e:
            raise LeadNotFoundError(str(e))
    lead = await lead_collection.find_one(query, sort=[("created_time", -1)])
    if not lead:
        raise LeadNotFoundError("Lead not found with the provided information.")

    return lead


async def create_lead(lead: lead.LeadModel):
    lead_collection = get_lead_collection()
    new_lead = await lead_collection.insert_one(
        lead.model_dump(by_alias=True, exclude=["id"])
    )
    return new_lead


async def get_all_leads(page, limit, sort, filter):
    pipeline = []
    if filter:
        if "q" in filter:
            query_value = filter["q"]
            query_filters = [
                {"first_name": {"$regex": query_value, "$options": "i"}},
                {"last_name": {"$regex": query_value, "$options": "i"}},
                {"email": {"$regex": query_value, "$options": "i"}},
                {"phone": {"$regex": query_value, "$options": "i"}}
            ]
            if filter.get("$or"):
                filter["$and"] = [{"$or": query_filters}, {"$or": filter.pop("$or")}]
            else:
                filter["$or"] = query_filters
            filter.pop("q")
        filter = _format_created_time_filter(filter)
        filter = _format_lead_sold_time_filter(filter)
        filter = _format_second_chance_lead_sold_time_filter(filter)
        if "lead_received_date" in filter:
            filter = _format_lead_received_date_filter()
        if "first_name" in filter:
            filter["first_name"] = {"$regex": str.capitalize(filter["first_name"]), "$options": "i"}
        if "last_name" in filter:
            filter["last_name"] = {"$regex": str.capitalize(filter["last_name"]), "$options": "i"}
        if "agent_id" in filter:
            if not filter["agent_id"]:
                return [], 0
            agent_id = filter.pop("agent_id")
            filter["$or"] = [
                {"buyer_id": agent_id},
                {"second_chance_buyer_id": agent_id}
            ]
            pipeline = [
                {"$match": filter},
                {"$sort": {sort[0]: sort[1]}},
                {"$skip": (page - 1) * limit},
                {"$limit": limit},
                {"$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "phone": 1,
                    "state": 1,
                    "origin": 1,
                    "lead_sold_time": 1,
                    "second_chance_lead_sold_time": 1,
                    "buyer_id": 1,
                    "second_chance_buyer_id": 1,
                    "lead_sold_by_agent_time": 1,
                    "campaign_id": 1,
                    "created_time": 1,
                    "custom_fields": 1,
                    "is_second_chance": 1,
                    "lead_received_date": {
                        "$cond": {
                            "if": {"$eq": ["$buyer_id", agent_id]},
                            "then": "$lead_sold_time",
                            "else": {
                                "$cond": {
                                    "if": {"$eq": ["$second_chance_buyer_id", agent_id]},
                                    "then": "$second_chance_lead_sold_time",
                                    "else": None
                                }
                            }
                        }
                    },
                    "lead_type": {
                        "$cond": {
                            "if": {"$eq": [agent_id, "$second_chance_buyer_id"]},
                            "then": "2nd Chance",
                            "else": "Fresh"
                        }
                    }
                }}
            ]

    lead_collection = get_lead_collection()
    if pipeline:
        leads = await lead_collection.aggregate(pipeline).to_list(None)
    else:
        leads = await lead_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
    if filter:
        total = await lead_collection.count_documents(filter)
    else:
        total = await lead_collection.count_documents({})
    return leads, total


async def get_one_lead(id):
    lead_collection = get_lead_collection()
    try:
        if (
            lead := await lead_collection.find_one({"_id": ObjectId(id)})
        ) is not None:
            return lead

        raise LeadNotFoundError(f"Lead with id {id} not found")
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on lead get one route")


async def delete_lead(id):
    lead_collection = get_lead_collection()
    try:
        delete_result = await lead_collection.delete_one({"_id": ObjectId(id)})
        return delete_result
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on delete lead route")


async def delete_leads(ids):
    lead_collection = get_lead_collection()
    result = await lead_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}})
    return result


def _format_created_time_filter(filter):
    if "created_time_gte" in filter or "created_time_lte" in filter:
        filter["created_time"] = {}
    if "created_time_gte" in filter:
        filter["created_time"]["$gte"] = datetime.strptime(filter.pop("created_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "created_time_lte" in filter:
        filter["created_time"]["$lte"] = datetime.strptime(filter.pop("created_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter

def _format_lead_received_date_filter(filter, date_gte, date_lte, agent_id):

    if date_gte or date_lte:
        date_filter = {}
        if date_gte:
            date_filter["$gte"] = datetime.strptime(date_gte, "%Y-%m-%dT%H:%M:%S.%fZ")
        if date_lte:
            date_filter["$lte"] = datetime.strptime(date_lte, "%Y-%m-%dT%H:%M:%S.%fZ")
        
        lead_receive_date_filter = {
            "$cond": {
                "if": {"$and": [
                    {"$eq": ["$buyer_id", agent_id]},
                    {"$gte": ["$lead_sold_time", date_filter.get("$gte", datetime.min)]},
                    {"$lte": ["$lead_sold_time", date_filter.get("$lte", datetime.max)]}
                ]},
                "then": "$lead_sold_time",
                "else": {
                    "$cond": {
                        "if": {"$and": [
                            {"$eq": ["$second_chance_buyer_id", agent_id]},
                            {"$gte": ["$second_chance_lead_sold_time", date_filter.get("$gte", datetime.min)]},
                            {"$lte": ["$second_chance_lead_sold_time", date_filter.get("$lte", datetime.max)]}
                        ]},
                        "then": "$second_chance_lead_sold_time",
                        "else": None
                    }
                }
            }
        }
    
    filter["cond"] = lead_receive_date_filter
    return filter

def _format_lead_sold_time_filter(filter):
    if "lead_sold_time_gte" in filter or "lead_sold_time_lte" in filter:
        filter["lead_sold_time"] = {}
    if "lead_sold_time_gte" in filter:
        filter["lead_sold_time"]["$gte"] = datetime.strptime(filter.pop("lead_sold_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "lead_sold_time_lte" in filter:
        filter["lead_sold_time"]["$lte"] = datetime.strptime(filter.pop("lead_sold_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter


def _format_second_chance_lead_sold_time_filter(filter):
    if "second_chance_lead_sold_time_gte" in filter or "second_chance_lead_sold_time_lte" in filter:
        filter["second_chance_lead_sold_time"] = {}
    if "second_chance_lead_sold_time_gte" in filter:
        filter["second_chance_lead_sold_time"]["$gte"] = datetime.strptime(filter.pop("second_chance_lead_sold_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "second_chance_lead_sold_time_lte" in filter:
        filter["second_chance_lead_sold_time"]["$lte"] = datetime.strptime(filter.pop("second_chance_lead_sold_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter
