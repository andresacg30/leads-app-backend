from bson import ObjectId
from pymongo import ReturnDocument

from app.db import db
from app.models import campaign


campaign_collection = db["campaign"]


class CampaignNotFoundError(Exception):
    pass


async def get_campaign_by_name(campaign_name: str):
    campaign = await campaign_collection.find_one({"name": campaign_name})
    return campaign


async def create_campaign(campaign: campaign.CampaignModel):
    new_campaign = await campaign_collection.insert_one(
        campaign.model_dump(by_alias=True, exclude=["id"])
    )
    return new_campaign


async def get_all_campaigns(page, limit):
    campaigns = await campaign_collection.find().skip((page - 1) * limit).limit(limit).to_list(limit)
    return campaigns


async def get_one_campaign(id):
    if (
        campaign := await campaign_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return campaign

    raise CampaignNotFoundError(f"Campaign with id {id} not found")


async def update_campaign(id, campaign: campaign.UpdateCampaignModel):
    update_result = await campaign_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": campaign},
            return_document=ReturnDocument.AFTER,
        )
    return update_result


async def delete_campaign(id):
    delete_result = await campaign_collection.delete_one({"_id": ObjectId(id)})
    return delete_result