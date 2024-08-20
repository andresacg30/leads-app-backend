from bson import ObjectId
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.models import campaign


def get_campaign_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["campaign"]


class CampaignNotFoundError(Exception):
    pass


class CampaignIdInvalidError(Exception):
    pass


async def get_campaign_by_name(campaign_name: str):
    campaign_collection = get_campaign_collection()
    campaign = await campaign_collection.find_one({"name": campaign_name})
    return campaign


async def create_campaign(campaign: campaign.CampaignModel):
    campaign_collection = get_campaign_collection()
    new_campaign = await campaign_collection.insert_one(
        campaign.model_dump(by_alias=True, exclude=["id"])
    )
    return new_campaign


async def get_all_campaigns(page, limit, sort, filter):
    campaign_collection = get_campaign_collection()
    field, order = sort
    sort_dict = {field: order}
    campaigns = await campaign_collection.find(filter).sort(sort_dict).skip((page - 1) * limit).limit(limit).to_list(limit)
    return campaigns


async def get_one_campaign(id):
    campaign_collection = get_campaign_collection()
    if (
        campaign := await campaign_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        return campaign

    raise CampaignNotFoundError(f"Campaign with id {id} not found")


async def update_campaign(id, campaign: campaign.UpdateCampaignModel):
    campaign_collection = get_campaign_collection()
    campaign = {k: v for k, v in campaign.model_dump(by_alias=True).items() if v is not None}

    if len(campaign) >= 1:
        update_result = await campaign_collection.find_one_and_update(
            {"_id": ObjectId(id)},
            {"$set": campaign},
            return_document=ReturnDocument.AFTER,
        )

        if update_result is not None:
            return update_result

        else:
            raise CampaignNotFoundError(f"Campaign with id {id} not found")

    if (existing_campaign := await campaign_collection.find_one({"_id": id})) is not None:
        return existing_campaign

    return update_result


async def delete_campaign(id):
    campaign_collection = get_campaign_collection()
    delete_result = await campaign_collection.delete_one({"_id": ObjectId(id)})
    return delete_result


async def get_campaigns(ids):
    campaign_collection = get_campaign_collection()
    campaigns = await campaign_collection.find({"_id": {"$in": [ObjectId(id) for id in ids]}}).to_list(None)
    return campaigns


async def delete_campaigns(ids):
    campaign_collection = get_campaign_collection()
    result = await campaign_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}})
    return result
