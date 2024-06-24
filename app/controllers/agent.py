import difflib

from app.db import db


agent_collection = db["agent"]


async def get_agent_by_field(field, value):
    if field == "full_name":
        first_name, last_name = value.split(' ')
        agent = await agent_collection.find_one({"first_name": first_name, "last_name": last_name})
        if agent is None:
            agents = await agent_collection.find().to_list(None)
            full_names = [f"{a['first_name']} {a['last_name']}" for a in agents]
            closest_match = difflib.get_close_matches(value, full_names, n=1)
            if closest_match:
                first_name, last_name = closest_match[0].split(' ')
                agent = await agent_collection.find_one({"first_name": first_name, "last_name": last_name})
                return agent
            else:
                # send notification
                return None
    agent = await agent_collection.find_one({field: value})
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


def format_state_list(states):
    state_list = states[0].split(', ')
    return state_list
