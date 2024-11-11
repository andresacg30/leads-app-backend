import asyncio
import bson
import datetime
import logging

from collections import defaultdict
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from motor.core import AgnosticCollection

from main import stripe
from app.auth import jwt_handler
from app.db import Database
from app.resources import user_connections
from app.controllers import agent as agent_controller
from app.models.agent import AgentModel
from app.models import user as user_model
from app.tools import jwt_helper
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


async def create_user(user):
    agent_model = AgentModel(
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        phone=user["phone"],
        states_with_license=user["states_with_license"],
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
        otp_expiration=datetime.datetime.utcnow() + datetime.timedelta(seconds=OTP_EXPIRATION),
    )
    stripe_customer_id = _create_stripe_customer(user)
    user.stripe_customer_id = stripe_customer_id

    user_collection = get_user_collection()
    user.password = jwt_helper.encrypt(user.password)
    new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"], mode="python"))
    return new_user


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


def _create_stripe_customer(user: user_model.UserModel):
    stripe_customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        phone=user.phone,
    )

    return stripe_customer["id"]


async def change_user_permissions(user_id, new_permissions):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one_and_update(
        {"_id": bson.ObjectId(user_id)},
        {"$set": {"permissions": new_permissions}},
        return_document=True
    )
    return jwt_handler.create_access_token(str(user_in_db["email"]), user_in_db["permissions"])


async def onboard_user(user: user_model.UserModel):
    user_collection = get_user_collection()
    user_in_db = await user_collection.find_one({"_id": bson.ObjectId(user.id)})
    await user_collection.update_one(
        {"_id": bson.ObjectId(user.id)},
        {"$set": {"campaigns": [bson.ObjectId("6668b634a88f8e5a8dde197e")]}}
    )
    await agent_controller.update_campaigns_for_agent(user_in_db["agent_id"], [bson.ObjectId("6668b634a88f8e5a8dde197e")])
    return user


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
    logger.info(f"Checking user {user_id} is verified")
    user_collection = get_user_collection()
    user = await user_collection.find_one({"_id": bson.ObjectId(user_id)})
    if not user["email_verified"]:
        logger.info(f"User {user_id} not verified, deleting")
        agent_collection = agent_controller.get_agent_collection()
        await agent_collection.delete_one({"_id": bson.ObjectId(user["agent_id"])})
        await user_collection.delete_one({"_id": bson.ObjectId(user_id)})
        logger.info(f"User {user_id} deleted")
        return False


async def get_user_balance(id: str):
    user_collection = get_user_collection()
    user = await user_collection.find_one({"agent_id": bson.ObjectId(id)})
    return user["balance"]
