from datetime import datetime, timedelta
import bson
import difflib

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.controllers.lead import get_lead_collection
from app.models.agent import AgentModel, UpdateAgentModel


def get_agent_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["agent"]


class AgentNotFoundError(Exception):
    pass


class AgentIdInvalidError(Exception):
    pass


class AgentEmptyError(Exception):
    pass


async def get_agent_by_field(**kwargs):
    agent_collection = get_agent_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}

    if "full_name" in query:
        full_name = query.pop("full_name")
        first_name = full_name.split(' ')[0]
        last_name = " ".join(full_name.split(' ')[1:])
        agent = await agent_collection.find_one({"first_name": first_name, "last_name": last_name})
        if agent is None:
            agents = await agent_collection.find().to_list(None)
            full_names = [f"{a['first_name']} {a['last_name']}" for a in agents]
            closest_match = difflib.get_close_matches(full_name, full_names, n=1)
            if closest_match:
                first_name = closest_match[0].split(' ')[0]
                last_name = " ".join(closest_match[0].split(' ')[1:])
                agent = await agent_collection.find_one({"first_name": first_name, "last_name": last_name})
                if not agent:
                    raise AgentNotFoundError(f"Agent with full name {full_name} not found")
                return agent
            else:
                # send notification
                raise AgentNotFoundError(f"No close match for agent with full name {full_name}")
        return agent

    agent = await agent_collection.find_one(query)

    if not agent:
        raise AgentNotFoundError("Agent not found with the provided information.")

    return agent


async def get_enrolled_campaigns(agent_id):
    agent_collection = get_agent_collection()
    try:
        agent = await agent_collection.find_one({"_id": ObjectId(agent_id)})
        enrolled_campaigns = agent['campaigns']
        return enrolled_campaigns
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {agent_id} on get enrolled campaigns function / create agent route.")


async def update_campaigns_for_agent(agent_id, campaigns):
    agent_collection = get_agent_collection()
    updated_agent = await agent_collection.update_one(
        {"_id": agent_id}, {"$set": {"campaigns": campaigns}}
    )
    return updated_agent


async def create_agent(agent: AgentModel):
    agent_collection = get_agent_collection()
    created_agent = await agent_collection.insert_one(
        agent.model_dump(by_alias=True, exclude=["id", "full_name"], mode="python")
    )
    return created_agent


async def get_all_agents(page, limit, sort, filter):
    pipeline = []
    if filter:
        filter = _filter_formatter_helper(filter)
        if "user_campaigns" in filter:
            campaigns = filter.pop("user_campaigns")
            filter["campaigns"] = {"$in": campaigns}
            pipeline = [
                {"$match": filter},
                {"$sort": {sort[0]: sort[1]}},
                {"$skip": (page - 1) * limit},
                {"$limit": limit},
                {"$lookup": {
                    "from": "user",
                    "localField": "_id",
                    "foreignField": "agent_id",
                    "as": "user_info"
                    }},
                {"$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                    }},
                {"$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "phone": 1,
                    "states_with_license": 1,
                    "CRM": 1,
                    "balance": {
                        "$ifNull": ["$user_info.balance", 0]
                        },
                    "created_time": 1,
                    "campaigns": {
                        "$filter": {
                            "input": "$campaigns",
                            "as": "campaign",
                            "cond": {"$in": ["$$campaign", campaigns]}
                        }
                    },
                    "credentials": 1,
                    "custom_fields": 1
                }}
            ]
    agent_collection = get_agent_collection()
    if pipeline:
        agents = await agent_collection.aggregate(pipeline).to_list(None)
    else:
        agents = await agent_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
    if filter:
        total = await agent_collection.count_documents(filter)
    else:
        total = await agent_collection.count_documents({})
    return agents, total


async def get_agent(id):
    from app.controllers.user import get_user_balance
    agent_collection = get_agent_collection()
    try:
        agent_in_db = await agent_collection.find_one({"_id": ObjectId(id)})
        agent_balance = await get_user_balance(id)
        agent = AgentModel(**agent_in_db)
        agent.balance = agent_balance
        return agent
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on get agent route.")


async def update_agent(id, agent: UpdateAgentModel):
    if all([v is None for v in agent.model_dump(mode="python").values()]):
        raise AgentEmptyError("Empty agent fields provided for update.")
    agent_collection = get_agent_collection()
    try:
        agent = {k: v for k, v in agent.model_dump(by_alias=True, mode="python").items() if v is not None}

        if len(agent) >= 1:
            update_result = await agent_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": agent},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                return update_result

            else:
                raise AgentNotFoundError(f"Agent with id {id} not found")

        if (existing_agent := await agent_collection.find_one({"_id": id})) is not None:
            return existing_agent
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on update agent route.")


async def delete_agent(id):
    agent_collection = get_agent_collection()
    try:
        result = await agent_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on delete agent route.")


async def get_agents(ids):
    agent_collection = get_agent_collection()
    agents = await agent_collection.find({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}}).to_list(None)
    if not agents:
        raise AgentNotFoundError("Agents not found with the provided information.")
    return agents


async def delete_agents(ids):
    agent_collection = get_agent_collection()
    result = await agent_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}})
    return result


async def get_active_agents(user_campaigns):
    lead_collection = get_lead_collection()
    nine_days_ago = datetime.utcnow() - timedelta(days=9)

    pipeline = [
        {"$match": {
            "$or": [
                {"lead_sold_time": {"$gte": nine_days_ago}},
                {"second_chance_lead_sold_time": {"$gte": nine_days_ago}}
            ],
            "campaign_id": {"$in": user_campaigns},
        }},
        {"$project": {
            "buyer_ids": {
                "$cond": {
                    "if": {"$gte": ["$lead_sold_time", nine_days_ago]},
                    "then": "$buyer_id",
                    "else": None
                },
            },
            "second_chance_buyer_ids": {
                "$cond": {
                    "if": {"$gte": ["$second_chance_lead_sold_time", nine_days_ago]},
                    "then": "$second_chance_buyer_id",
                    "else": None
                }
            }
        }},
        {"$project": {
            "buyer_ids": {
                "$setUnion": [["$buyer_ids"], ["$second_chance_buyer_ids"]]
            }
        }},
        {"$unwind": "$buyer_ids"},
        {"$match": {"buyer_ids": {"$ne": None}}},
        {"$project": {
            "buyer_ids": {"$toString": "$buyer_ids"}
        }},
        {"$group": {
            "_id": None,
            "unique_buyer_ids": {"$addToSet": "$buyer_ids"}
        }}
    ]

    result = await lead_collection.aggregate(pipeline).to_list(length=None)
    active_agents = result[0]["unique_buyer_ids"] if result else []
    total = len(active_agents)
    return active_agents, total


def _filter_formatter_helper(filter):
    filter["created_time"] = {}
    if "q" in filter:
        query_value = filter["q"]
        filter["$or"] = [
            {"first_name": {"$regex": query_value, "$options": "i"}},
            {"last_name": {"$regex": query_value, "$options": "i"}},
            {"email": {"$regex": query_value, "$options": "i"}},
            {"phone": {"$regex": query_value, "$options": "i"}}
        ]
        filter.pop("q")
    if "created_time_gte" not in filter and "created_time_lte" not in filter:
        filter.pop("created_time")
    if "created_time_gte" in filter:
        filter["created_time"]["$gte"] = datetime.strptime(filter.pop("created_time_gte"), "%Y-%m-%dT%H:%M:%S.000Z")
    if "created_time_lte" in filter:
        filter["created_time"]["$lte"] = datetime.strptime(filter.pop("created_time_lte"), "%Y-%m-%dT%H:%M:%S.000Z")
    if "first_name" in filter:
        filter["first_name"] = {"$regex": str.capitalize(filter["first_name"]), "$options": "i"}
    if "last_name" in filter:
        filter["last_name"] = {"$regex": str.capitalize(filter["last_name"]), "$options": "i"}
    return filter


async def get_agents_with_balance(campaign: ObjectId):
    agent_collection = get_agent_collection()
    pipeline = [
                {"$match": {"campaigns": campaign}},
                {"$lookup": {
                    "from": "user",
                    "localField": "_id",
                    "foreignField": "agent_id",
                    "as": "user_info"
                    }},
                {"$unwind": {
                    "path": "$user_info",
                    "preserveNullAndEmptyArrays": True
                    }},
                {"$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "phone": 1,
                    "states_with_license": 1,
                    "CRM": 1,
                    "balance": {
                        "$ifNull": ["$user_info.balance", 0]
                        },
                    "created_time": 1,
                    "campaigns": 1,
                    "credentials": 1,
                    "custom_fields": 1
                }},
                {"$match": {"balance": {"$gt": 0}}}
            ]
    agents = await agent_collection.aggregate(pipeline).to_list(None)
    return agents
