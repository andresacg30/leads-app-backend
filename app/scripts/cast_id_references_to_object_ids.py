from bson.objectid import ObjectId
from bson.errors import InvalidId
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
        def to_objectid(value):
            if value and value not in ["null", ""]:
                try:
                    return ObjectId(value)
                except InvalidId:
                    pass
            return None

        campaign_id = to_objectid(lead.get("campaign_id"))
        buyer_id = to_objectid(lead.get("buyer_id"))
        second_chance_buyer_id = to_objectid(lead.get("second_chance_buyer_id"))

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
