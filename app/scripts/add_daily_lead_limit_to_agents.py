from app.db import Database
from pymongo import UpdateMany


async def daily_lead_limit_creation():
    agent_collection = Database().get_db()["agent"]
    try:
        agents = await agent_collection.find({}).to_list(None)
        updates = []
        for agent in agents:
            campaigns = agent.get("campaigns", [])
            daily_limit = [
                {
                    "campaign_id": campaign_id,
                    "limit": 12
                }
                for campaign_id in campaigns
            ]
            updates.append(UpdateMany(
                {"_id": agent["_id"]},
                {"$set": {"daily_lead_limit": daily_limit}},
                upsert=True
            ))
        if updates:
            await agent_collection.bulk_write(updates)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print(f"Daily lead limit creation completed. Updated documents: {len(updates)}")
