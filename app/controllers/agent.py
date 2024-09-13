from datetime import datetime
import bson
import difflib

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
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
        agent.model_dump(by_alias=True, exclude=["id"])
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
                {"$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "phone": 1,
                    "states_with_license": 1,
                    "CRM": 1,
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
    agent_collection = get_agent_collection()
    try:
        agent_in_db = await agent_collection.find_one({"_id": ObjectId(id)})
        return agent_in_db
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on get agent route.")


async def update_agent(id, agent: UpdateAgentModel):
    if all([v is None for v in agent.model_dump().values()]):
        raise AgentEmptyError("Empty agent fields provided for update.")
    agent_collection = get_agent_collection()
    try:
        agent = {k: v for k, v in agent.model_dump(by_alias=True).items() if v is not None}

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
