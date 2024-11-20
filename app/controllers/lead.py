import bson
import logging
import random

from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument
from typing import List
from motor.core import AgnosticCollection


from app.db import Database
from app.background_jobs import lead as lead_background_jobs
from app.models import lead as lead_model
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.tools import formatters as formatter
from app.tools import constants


logger = logging.getLogger(__name__)


def get_lead_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["lead"]


class LeadNotFoundError(Exception):
    pass


class LeadIdInvalidError(Exception):
    pass


class LeadEmptyError(Exception):
    pass


async def update_lead(id, lead: lead_model.UpdateLeadModel):
    if all(v is None for v in lead.model_dump(mode="python").values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True, mode="python").items() if v is not None}
        datetime_fields = ["created_time", "lead_sold_time", "second_chance_lead_sold_time", "lead_sold_by_agent_time"]
        if any(field in lead for field in datetime_fields):
            for field in datetime_fields:
                if field in lead:
                    lead[field] = formatter.format_string_to_utc_datetime(lead[field])
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


async def update_lead_from_ghl(id, lead: lead_model.UpdateLeadModel):
    if all(v is None for v in lead.model_dump(mode="python").values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True, mode="python").items() if v is not None}
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
    from app.controllers import agent as agent_controller
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


async def create_lead(lead: lead_model.LeadModel):
    lead_collection = get_lead_collection()
    new_lead = await lead_collection.insert_one(
        lead.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    if str(lead.campaign_id) not in constants.OG_CAMPAIGNS:
        lead_background_jobs.process_lead(lead, lead_id=new_lead.inserted_id)
    return new_lead


async def get_all_leads(page, limit, sort, filter):
    if not filter:
        filter = {}

    filter = build_query_filters(filter)
    filter, date_gte, date_lte = _handle_lead_received_date_filter(filter)

    if "first_name" in filter:
        filter["first_name"] = {"$regex": str.capitalize(filter["first_name"]), "$options": "i"}
    if "last_name" in filter:
        filter["last_name"] = {"$regex": str.capitalize(filter["last_name"]), "$options": "i"}
    if "agent_id" in filter:
        if not filter["agent_id"]:
            return [], 0
        agent_id = filter.pop("agent_id")
        filter["$or"] = [
            {"buyer_id": ObjectId(agent_id)},
            {"second_chance_buyer_id": ObjectId(agent_id)}
        ]
        pipeline = _build_aggregation_pipeline(filter, sort, page, limit, agent_id, date_gte, date_lte)
    else:
        pipeline = []

    lead_collection = get_lead_collection()
    if pipeline:
        result = await lead_collection.aggregate(pipeline).to_list(None)
        leads = result[0]["data"]
        total = result[0]["total"][0]["count"] if result[0]["total"] else 0
    else:
        leads_in_db = await lead_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
        leads = [lead_model.LeadModel(**lead).to_json() for lead in leads_in_db]
        total = await lead_collection.count_documents(filter) if filter else await lead_collection.count_documents({})

    return leads, total


async def get_one_lead(id):
    lead_collection = get_lead_collection()
    try:
        if (
            lead_in_db := await lead_collection.find_one({"_id": ObjectId(id)})
        ) is not None:
            lead = lead_model.LeadModel(**lead_in_db)
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


def build_query_filters(filter):
    #  Whenever i wrote this code, God and I knew how it worked. Now God only knows. Good luck! Attempts to refactor: 69  <- Add yours
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
    if "buyer_id" in filter:
        filter["buyer_id"] = ObjectId(filter["buyer_id"])
    if "second_chance_buyer_id" in filter:
        filter["second_chance_buyer_id"] = ObjectId(filter["second_chance_buyer_id"])
    filter = _format_created_time_filter(filter)
    filter = _format_lead_sold_time_filter(filter)
    filter = _format_second_chance_lead_sold_time_filter(filter)
    return filter


def _handle_lead_received_date_filter(filter):
    if "lead_received_date_gte" in filter or "lead_received_date_lte" in filter:
        date_gte = filter.pop("lead_received_date_gte", None)
        date_lte = filter.pop("lead_received_date_lte", None)
        if date_gte:
            date_gte = datetime.strptime(date_gte, "%Y-%m-%dT%H:%M:%S.%fZ")
        if date_lte:
            date_lte = datetime.strptime(date_lte, "%Y-%m-%dT%H:%M:%S.%fZ")
        return filter, date_gte, date_lte
    return filter, None, None


def _build_aggregation_pipeline(filter, sort, page, limit, agent_id, date_gte, date_lte):
    match_conditions = []

    if filter:
        match_conditions.append(filter)

    lead_received_date_expr = {
        "$cond": [
            {"$eq": ["$buyer_id", agent_id]},
            "$lead_sold_time",
            {
                "$cond": [
                    {"$eq": ["$second_chance_buyer_id", agent_id]},
                    "$second_chance_lead_sold_time",
                    None
                ]
            }
        ]
    }

    date_expr_conditions = []
    if date_gte:
        date_expr_conditions.append({"$gte": [lead_received_date_expr, date_gte]})
    if date_lte:
        date_expr_conditions.append({"$lte": [lead_received_date_expr, date_lte]})

    if date_expr_conditions:
        if len(date_expr_conditions) == 1:
            date_condition = date_expr_conditions[0]
        else:
            date_condition = {"$and": date_expr_conditions}
        match_conditions.append({"$expr": date_condition})

    if match_conditions:
        if len(match_conditions) == 1:
            match_stage = {"$match": match_conditions[0]}
        else:
            match_stage = {"$match": {"$and": match_conditions}}
    else:
        match_stage = {"$match": {}}

    pipeline = [
        match_stage,
        {
            "$addFields": {
                "lead_received_date": lead_received_date_expr,
                "lead_type": {
                    "$cond": [
                        {"$eq": [agent_id, "$second_chance_buyer_id"]},
                        "2nd Chance",
                        "Fresh"
                    ]
                },
                "is_second_chance": {
                    "$eq": ["$lead_type", "2nd Chance"]
                }
            }
        },
        {
            "$project": {
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
                "lead_received_date": 1,
                "lead_type": 1,
                "is_second_chance": 1
            }
        },
        {
            "$facet": {
                "data": [
                    {"$sort": {sort[0]: sort[1]}},
                    {"$skip": (page - 1) * limit},
                    {"$limit": limit}
                ],
                "total": [
                    {"$count": "count"}
                ]
            }
        }
    ]

    return pipeline


async def get_leads(ids: List[ObjectId], user: UserModel):
    lead_collection = get_lead_collection()
    if user.is_agent():
        lead_received_date_expr = {
            "$cond": [
                {"$eq": ["$buyer_id", user.agent_id]},
                "$lead_sold_time",
                {
                    "$cond": [
                        {"$eq": ["$second_chance_buyer_id", user.agent_id]},
                        "$second_chance_lead_sold_time",
                        None
                    ]
                }
            ]
        }
        match_conditions = {"_id": {"$in": [ObjectId(id) for id in ids]}}
        pipeline = [
            {"$match": match_conditions},
            {
                "$addFields": {
                    "lead_received_date": lead_received_date_expr,
                    "lead_type": {
                        "$cond": [
                            {"$eq": [user.agent_id, "$second_chance_buyer_id"]},
                            "2nd Chance",
                            "Fresh"
                        ]
                    },
                    "is_second_chance": {
                        "$eq": ["$lead_type", "2nd Chance"]
                    }
                }
            },
            {
                "$project": {
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
                    "lead_received_date": 1,
                    "lead_type": 1,
                    "is_second_chance": 1
                }
            },
        ]
        leads_in_db = await lead_collection.aggregate(pipeline).to_list(None)
    else:
        leads_in_db = await lead_collection.find({"_id": {"$in": [ObjectId(id) for id in ids]}}).to_list(None)
    leads = [lead_model.LeadModel(**lead).to_json() for lead in leads_in_db]
    return leads


async def assign_lead_to_agent(lead: lead_model.LeadModel, lead_id: str):
    from app.controllers import agent as agent_controller
    from app.controllers import transaction as transaction_controller
    from app.controllers import user as user_controller
    lead_price = 25
    lead_collection = get_lead_collection()
    lead = lead.model_dump(by_alias=True, mode="python")
    formatted_lead_state = formatter.format_state_to_abbreviation(lead["state"])
    agents_with_balance = await agent_controller.get_agents_with_balance(campaign=lead["campaign_id"])
    if not agents_with_balance:
        logger.warning(f"No agents with balance found for lead {lead_id}")
        return
    agents_licensed_in_lead_state = [
        agent for agent in agents_with_balance if formatted_lead_state in agent["states_with_license"] and agent["balance"] >= lead_price
    ]
    if not agents_licensed_in_lead_state:
        logger.warning(f"No agents licensed in {formatted_lead_state} with balance found for lead {lead_id}")
        return
    agent_to_distribute = choose_agent(agents=agents_licensed_in_lead_state, distribution_type="round_robin")
    if agent_to_distribute:
        result = await lead_collection.update_one(
            {"_id": lead_id},
            {"$set": {
                "buyer_id": agent_to_distribute["_id"],
                "lead_sold_time": datetime.utcnow()
            }}
        )
        if result.modified_count == 1:
            user = await user_controller.get_user_by_field(agent_id=agent_to_distribute["_id"])
            user_id = user.id
            await transaction_controller.create_transaction(
                TransactionModel(
                    user_id=user_id,
                    amount=-lead_price,
                    description="Fresh Lead purchase",
                    type="debit",
                    date=datetime.utcnow()
                )
            )
            return True


def choose_agent(agents, distribution_type):
    if distribution_type == "round_robin":
        return agents[0]
    elif distribution_type == "random":
        return random.choice(agents)


async def send_leads_to_agent(lead_ids: list, agent_id: str):
    from app.controllers import agent as agent_controller
    from app.controllers import transaction as transaction_controller
    from app.controllers import user as user_controller
    lead_collection = get_lead_collection()
    agent_id_obj = ObjectId(agent_id)
    agent = await agent_controller.get_agent_by_field(_id=agent_id_obj)
    if not agent:
        logger.warning(f"Agent {agent_id} not found")
        return
    result = await lead_collection.update_many(
        {"_id": {"$in": [ObjectId(id) for id in lead_ids]}},
        {"$set": {
            "buyer_id": agent_id_obj,
            "lead_sold_time": datetime.utcnow()
        }}
    )
    user = await user_controller.get_user_by_field(agent_id=agent_id_obj)
    user_id = user.id
    lead_price = 25
    await transaction_controller.create_transaction(
        TransactionModel(
            user_id=user_id,
            amount=-lead_price * len(lead_ids),
            description="Leads sent by agency",
            type="debit",
            date=datetime.utcnow()
        )
    )
    if result.modified_count == len(lead_ids):
        return True
    return False
