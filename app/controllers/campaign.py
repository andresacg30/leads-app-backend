import uuid
from bson import ObjectId
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

import app.integrations.stripe as stripe_integration

from app.db import Database
from app.models import campaign as campaign_models


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


async def create_campaign(campaign: campaign_models.CampaignModel):
    import app.controllers.user as user_controller
    campaign_collection = get_campaign_collection()
    sign_up_code = generate_unique_sign_up_code()
    campaign.sign_up_code = sign_up_code
    campaign.status = "onboarding"
    admin_user = await user_controller.get_user_by_field(_id=campaign.admin_id)
    stripe_account, stripe_account_onboarding_url = await stripe_integration.create_stripe_connect_account(admin_user.email)
    campaign.stripe_account_onboarding_url = stripe_account_onboarding_url.url
    campaign.stripe_account_id = stripe_account.id
    new_campaign = await campaign_collection.insert_one(
        campaign.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    campaign.id = new_campaign.inserted_id
    await user_controller.onboard_agency_admin(campaign=campaign, user=admin_user)
    return new_campaign


async def get_all_campaigns(page, limit, sort, filter):
    if "id" in filter:
        filter = {"_id": {"$in": [ObjectId(id) for id in filter["id"]]}}
    campaign_collection = get_campaign_collection()
    campaigns = await campaign_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
    total = await campaign_collection.count_documents({})
    return campaigns, total


async def get_one_campaign(id):
    campaign_collection = get_campaign_collection()
    if (
        campaign_in_db := await campaign_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        campaign_result = campaign_models.CampaignModel(**campaign_in_db)
        return campaign_result

    raise CampaignNotFoundError(f"Campaign with id {id} not found")


async def update_campaign(id, campaign: campaign_models.UpdateCampaignModel):
    from app.controllers.user import onboard_agency_admin, remove_campaign_from_user
    campaign_collection = get_campaign_collection()
    campaign = {k: v for k, v in campaign.model_dump(by_alias=True, mode="python").items() if v is not None}
    campaign_model = campaign_models.CampaignModel(**campaign)

    if "admin_id" in campaign:
        if campaign_model.admin_id:
            await remove_campaign_from_user(id)
        if campaign_model.status == "onboarding":
            campaign_model.id = id
            await onboard_agency_admin(campaign_model)

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
    campaigns_in_db = await campaign_collection.find({"_id": {"$in": [ObjectId(id) for id in ids]}}).to_list(None)
    campaigns = [campaign_models.CampaignModel(**campaign_in_db).to_json() for campaign_in_db in campaigns_in_db]
    return campaigns


async def delete_campaigns(ids):
    campaign_collection = get_campaign_collection()
    result = await campaign_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}})
    return result


async def get_campaign_by_sign_up_code(sign_up_code):
    campaign_collection = get_campaign_collection()
    campaign_in_db = await campaign_collection.find_one({"sign_up_code": sign_up_code})
    campaign_result = campaign_models.CampaignModel(**campaign_in_db)
    return campaign_result


def generate_unique_sign_up_code():
    uid = uuid.uuid4()
    code = uid.int % 1_000_000
    return f"{code:06d}"


async def get_campaign_by_admin_id(admin_id: ObjectId):
    campaign_collection = get_campaign_collection()
    campaign_in_db = await campaign_collection.find_one({"admin_id": admin_id})
    if not campaign_in_db:
        return None
    campaign_result = campaign_models.CampaignModel(**campaign_in_db)
    return campaign_result


async def get_stripe_onboarding_url(campaign_id: ObjectId):
    campaign_collection = get_campaign_collection()
    campaign = await campaign_collection.find_one({"_id": campaign_id})
    stripe_account_onboarding_url = campaign["stripe_account_onboarding_url"]
    return stripe_account_onboarding_url


async def get_stripe_account_id(campaign_id: ObjectId):
    campaign_collection = get_campaign_collection()
    campaign = await campaign_collection.find_one({"_id": campaign_id})
    stripe_account_id = campaign["stripe_account_id"]
    return stripe_account_id
