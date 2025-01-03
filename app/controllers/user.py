import asyncio
import bson
import datetime
import logging

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from motor.core import AgnosticCollection

from app.auth import jwt_handler
from app.db import Database
from app.integrations.ringy import Ringy
from app.resources import user_connections
from app.controllers import agent as agent_controller
from app.controllers import campaign as campaign_controller
from app.models.agent import AgentModel
from app.models.campaign import CampaignModel
from app.models import user as user_model
from app.tools import jwt_helper, emails
from app.tools.constants import OTP_EXPIRATION


logger = logging.getLogger(__name__)


def get_user_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["user"]


class UserNotFoundError(Exception):
    pass


security = HTTPBasic()


async def validate_login(credentials: HTTPBasicCredentials = Depends(security)):
    user_collection = get_user_collection()
    user = user_collection.find_one({"email": credentials.username})
    if user:
        password = jwt_helper.verify(credentials.password, user["password"])
        if not password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        return True
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
    )


async def create_user(user) -> user_model.UserModel:
    from app.integrations.stripe import create_customer

    if not user["sign_up_codes"]:
        raise HTTPException(status_code=400, detail="No sign up codes provided")
    agent_model = AgentModel(
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        phone=user["phone"],
        states_with_license=user["states_with_license"],
        campaigns=user["campaigns"],
    )
    created_agent = await agent_controller.create_agent(agent_model)

    user["agent_id"] = created_agent.inserted_id
    user["permissions"] = ["new_user"]

    user = user_model.UserModel(
        name=f"{user['first_name']} {user['last_name']}",
        email=user["email"],
        password=user["password"],
        phone=user["phone"],
        region=user["region"],
        agent_id=user["agent_id"],  
        permissions=user["permissions"],
        otp_code=user["otp_code"],
        campaigns=user["campaigns"],
        otp_expiration=datetime.datetime.utcnow() + datetime.timedelta(seconds=OTP_EXPIRATION),
    )
    for campaign in user.campaigns:
        user_campaign = await campaign_controller.get_one_campaign(campaign)
        stripe_customer = await create_customer(user=user, stripe_account_id=user_campaign.stripe_account_id)
        user.stripe_customer_ids[str(user_campaign.id)] = stripe_customer.id
    user_collection = get_user_collection()
    user.password = jwt_helper.encrypt(user.password)
    new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"], mode="python"))
    user.id = str(new_user.inserted_id)
    return user


async def get_user_by_field(**kwargs) -> user_model.UserModel:
    user_collection = get_user_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}
    user_in_db = await user_collection.find_one(query)
    if not user_in_db:
        raise UserNotFoundError("User not found with the provided information.")
    user = user_model.UserModel(**user_in_db)
    return user


async def update_user(user: user_model.UserModel):
    user_collection = get_user_collection()
    await user_collection.update_one({"_id": bson.ObjectId(user.id)}, {"$set": user.model_dump(by_alias=True, exclude=["id"], mode="python")})
    return user


async def store_refresh_token(username: str, refresh_token: str):
    user_collection = get_user_collection()
    await user_collection.update_one(
        {"email": username},
        {"$set": {"refresh_token": refresh_token}}
    )


async def get_users(ids):
    user_collection = get_user_collection()
    users = await user_collection.find({"_id": {"$in": [bson.ObjectId(id) for id in ids if id != "null"]}}).to_list(None)
    if not users:
        raise UserNotFoundError("No users found with the provided information")
    return users


async def change_user_permissions(user_id, new_permissions):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one_and_update(
        {"_id": bson.ObjectId(user_id)},
        {"$set": {"permissions": new_permissions}},
        return_document=True
    )
    return jwt_handler.create_access_token(str(user_in_db["email"]), user_in_db["permissions"])


async def activate_user(email):
    user_collection = get_user_collection()
    user = await user_collection.find_one_and_update(
        {"email": email},
        {"$set": {"email_verified": True}},
        return_document=True
    )
    return user


async def update_user_balance(user_id, amount):
    user_collection = get_user_collection()
    user = await user_collection.find_one_and_update(
        {"_id": bson.ObjectId(user_id)},
        {"$inc": {"balance": amount}},
        return_document=True
    )
    return user


async def user_change_stream_listener():
    user_collection = get_user_collection()
    pipeline = [
        {
            '$match': {
                'operationType': 'update',
                'updateDescription.updatedFields.balance': {'$exists': True}
            }
        }
    ]
    while True:
        try:
            async with user_collection.watch(pipeline) as stream:
                logger.info("Change stream listener started")
                async for change in stream:
                    user_id = str(change['documentKey']['_id'])
                    updated_fields = change['updateDescription']['updatedFields']
                    balance = updated_fields.get('balance')
                    if balance is not None:
                        data = {'balance': balance}
                        if user_id in user_connections:
                            logger.info(f"Sending data to user {user_id}: {data}")
                            for client in user_connections[user_id][:]:
                                try:
                                    await client.send_json(data)
                                except Exception as e:
                                    logger.error(f"Error sending data to client {client}: {e}")
                                    user_connections[user_id].remove(client)
                                    logger.info(f"Removed client {client} from user_connections[{user_id}]")
        except asyncio.CancelledError:
            logger.info("Change stream listener cancelled")
            break
        except Exception as e:
            logger.error(f"Change stream listener error: {e}")
            await asyncio.sleep(5)


async def check_user_is_verified_and_delete(user_id):
    from app.integrations.stripe import delete_customer
    logger.info(f"Checking user {user_id} is verified")
    user_collection = get_user_collection()
    user = await user_collection.find_one({"_id": bson.ObjectId(user_id)})
    if not user["email_verified"]:
        logger.info(f"User {user_id} not verified, deleting")
        agent_collection = agent_controller.get_agent_collection()
        for campaign_id in user["campaigns"]:
            campaign = await campaign_controller.get_one_campaign(campaign_id)
            await delete_customer(user, campaign)
        await agent_collection.delete_one({"_id": bson.ObjectId(user["agent_id"])})
        await user_collection.delete_one({"_id": bson.ObjectId(user_id)})
        logger.info(f"User {user_id} deleted")
        return False


async def get_user_balance_by_agent_id(id: str):
    user_collection = get_user_collection()
    user = await user_collection.find_one({"agent_id": bson.ObjectId(id)}) or {}
    return user.get("balance") or 0


async def get_all_users(page, limit, sort, filter):
    user_collection = get_user_collection()
    pipeline = []

    if filter:
        pipeline.append({"$match": filter})

    pipeline.extend([
        {"$project": {
            "_id": 1,
            "name": 1,
            "email": 1,
            "region": 1,
            "phone": 1,
            "agent_id": 1,
            "balance": 1,
            "permissions": 1,
            "campaigns": 1,
            "email_verified": 1,
        }},
        {"$sort": {sort[0]: sort[1]}},
        {"$skip": (page - 1) * limit},
        {"$limit": limit}
    ])
    users = await user_collection.aggregate(pipeline).to_list(None)
    if filter:
        total = len(users)
    else:
        total = await user_collection.count_documents({})
    return users, total


async def onboard_agency_admin(campaign: CampaignModel, user=None):
    user_collection = get_user_collection()
    if not user:
        user_in_db = await user_collection.find_one({"_id": bson.ObjectId(campaign.admin_id)})
        user = user_model.UserModel(**user_in_db)
        if not user:
            raise UserNotFoundError(f"User with id {campaign['admin_id']} not found")
    user_collection.update_one(
        {"_id": bson.ObjectId(campaign.admin_id)},
        {
            "$set": {"permissions": ["agency_admin_onboarding"]},
            "$addToSet": {"campaigns": bson.ObjectId(campaign.id)}
        }
    )
    emails.send_stripe_onboarding_email(
        email=user.email,
        user_name=user.name,
        onboarding_url=campaign.stripe_account_onboarding_url,
        campaign=campaign.name
    )
    return


async def remove_campaign_from_user(user_id, campaign_id):
    user_collection = get_user_collection()
    user_collection.update_one(
        {"_id": bson.ObjectId(user_id)},
        {"$pull": {"campaigns": bson.ObjectId(campaign_id)}}
    )
    return


async def get_user_by_email(email):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one({"email": email})
    if not user_in_db:
        raise UserNotFoundError(f"User with email {email} not found")
    user = user_model.UserModel(**user_in_db)
    return user


async def get_user_by_stripe_id(stripe_id):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one({
        "$expr": {
            "$in": [
                stripe_id,
                {
                    "$map": {
                        "input": {
                            "$objectToArray": {
                                "$ifNull": ["$stripe_customer_ids", {}]
                            }
                        },
                        "as": "item",
                        "in": "$$item.v"
                    }
                }
            ]
        }
    })
    if not user_in_db:
        raise UserNotFoundError(f"User with stripe id {stripe_id} not found")
    user = user_model.UserModel(**user_in_db)
    return user


async def get_active_users(user_campaigns, user):
    user_collection = get_user_collection()
    pipeline = [
        {"$match": {
            "campaigns": {"$in": user_campaigns}
        }},
        {"$lookup": {
            "from": "order",
            "let": {"agent_id": "$agent_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$agent_id", "$$agent_id"]},
                            {"$eq": ["$status", "open"]},  # Assuming 'status' indicates order status
                            {"$in": ["$campaign_id", user_campaigns]}
                        ]
                    }
                }}
            ],
            "as": "open_orders"
        }},
        {"$addFields": {
            "has_open_order": {"$gt": [{"$size": "$open_orders"}, 0]}
        }},
        {"$match": {
            "$or": [
                {"has_subscription": True},
                {"has_open_order": True}
            ]
        }},
        {"$project": {
            "first_name": 1,
            "last_name": 1,
            "email": 1,
            "phone": 1,
            "balance": 1,
            "has_subscription": 1,
            "campaigns": 1,
            "has_open_order": 1,
            "name": 1,
            "region": 1,
            "password": ""
        }}
    ]

    result = await user_collection.aggregate(pipeline).to_list(length=None)
    users = [user_model.UserModel(**user).to_json() for user in result]
    total = len(result)
    return users, total


async def get_user_integration_details(user_id, campaign_id):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one({"_id": bson.ObjectId(user_id)})
    user = user_model.UserModel(**user_in_db)
    agent = await agent_controller.get_agent(user.agent_id)
    return agent.CRM.get_campaign_integration_details(campaign_id)


async def update_user_integration_details(user_id, campaign_id, integration_details):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one({"_id": bson.ObjectId(user_id)})
    user = user_model.UserModel(**user_in_db)
    agent = await agent_controller.get_agent(user.agent_id)
    agent.CRM.update_integration_details(campaign_id, integration_details)
    updated_agent = await agent_controller.update_agent(id=user.agent_id, agent=agent)
    if not updated_agent:
        raise Exception("Failed to update integration details")
    return updated_agent
