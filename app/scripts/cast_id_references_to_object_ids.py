from bson import ObjectId
from pymongo import UpdateMany

from app.db import Database


async def update_agent_references():
    agent_collection = Database().get_db()["agent"]
    updates = []

    async for agent in agent_collection.find():
        agent_id = agent["_id"]
        agent_campaigns = [ObjectId(campaign_id) for campaign_id in agent["campaigns"]]
        updates.append(UpdateMany(
            {"_id": agent_id},
            {"$set": {"campaigns": agent_campaigns}}
        ))
    if updates:
        await agent_collection.bulk_write(updates)


async def update_lead_references():
    lead_collection = Database().get_db()["lead"]
    updates = []

    async for lead in lead_collection.find():
        campaign_id = ObjectId(lead["campaign_id"])
        if "buyer_id" not in lead:
            lead["buyer_id"] = "null"
        buyer_id = ObjectId(lead["buyer_id"]) if lead["buyer_id"] != "null" else None
        if "second_chance_buyer_id" not in lead:
            lead["second_chance_buyer_id"] = "null"
        second_chance_buyer_id = ObjectId(lead["second_chance_buyer_id"]) if lead["second_chance_buyer_id"] != "null" else None
        updates.append(UpdateMany(
            {"_id": lead["_id"]},
            {"$set": {
                "campaign_id": campaign_id,
                "buyer_id": buyer_id,
                "second_chance_buyer_id": second_chance_buyer_id
            }}
        ))
    if updates:
        await lead_collection.bulk_write(updates)
        print("Updated lead references")
