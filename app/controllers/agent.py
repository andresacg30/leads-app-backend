from app.db import db


agent_collection = db["agent"]


async def get_agent_by_email(email):
    agent = await agent_collection.find_one({"email": email})
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
