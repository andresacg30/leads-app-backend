import difflib

from bson import ObjectId
from pymongo import ReturnDocument

from app.db import db
from app.models.agent import AgentModel, UpdateAgentModel


agent_collection = db["agent"]


class AgentNotFoundError(Exception):
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
    agent = await agent_collection.find_one({"_id": agent_id})
    enrolled_campaigns = agent['campaigns']
    return enrolled_campaigns


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


async def get_all_agents(page, limit):
    agents = await agent_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return agents


async def get_agent(id):
    agent_in_db = await agent_collection.find_one({"_id": ObjectId(id)})
    return agent_in_db


async def update_agent(id, agent: UpdateAgentModel):
    result = await agent_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": agent},
            return_document=ReturnDocument.AFTER,
        )
    return result


async def delete_agent(id):
    result = await agent_collection.delete_one({"_id": ObjectId(id)})
    return result
