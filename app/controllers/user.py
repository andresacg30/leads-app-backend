import bson
import datetime

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from motor.core import AgnosticCollection

from main import stripe
from app.auth import jwt_handler
from app.db import Database
from app.controllers import agent as agent_controller
from app.models.agent import AgentModel
from app.models import user as user_model
from app.tools import jwt_helper
from app.tools.constants import OTP_EXPIRATION


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


async def get_user_by_field(**kwargs):
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
