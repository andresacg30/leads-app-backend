import bson
import difflib

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument

from app.db import db
from app.models.agent import AgentModel, UpdateAgentModel


agent_collection = db["agent"]


class AgentNotFoundError(Exception):
    pass


class AgentIdInvalidError(Exception):
    pass


async def get_agent_by_field(**kwargs):
    # Filter out None values from kwargs
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
    try:
        agent = await agent_collection.find_one({"_id": ObjectId(agent_id)})
        enrolled_campaigns = agent['campaigns']
        return enrolled_campaigns
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {agent_id} on get enrolled campaigns function / create agent route.")


async def update_campaigns_for_agent(agent_id, campaigns):
    updated_agent = await agent_collection.update_one(
        {"_id": agent_id}, {"$set": {"campaigns": campaigns}}
    )
    return updated_agent


async def create_agent(agent: AgentModel):
    created_agent = await agent_collection.insert_one(
        agent.model_dump(by_alias=True, exclude=["id"])
    )
    return created_agent


async def get_all_agents(page, limit, sort, filter):
    agents = await agent_collection.find(filter).sort(sort).skip((page - 1) * limit).limit(limit).to_list(limit)
    total = await agent_collection.count_documents({})
    return agents, total


async def get_agent(id):
    try:
        agent_in_db = await agent_collection.find_one({"_id": ObjectId(id)})
        return agent_in_db
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on get agent route.")


async def update_agent(id, agent: UpdateAgentModel):
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
    try:
        result = await agent_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise AgentIdInvalidError(f"Invalid id {id} on delete agent route.")
