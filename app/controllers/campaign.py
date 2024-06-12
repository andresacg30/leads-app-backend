from app.db import db


campaign_collection = db["campaign"]


async def get_campaign_by_name(campaign_name: str):
    campaign = await campaign_collection.find_one({"name": campaign_name})
    return campaign
