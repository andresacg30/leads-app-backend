import bson

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from motor.core import AgnosticCollection

from app.db import Database
from app.models import user
from app.tools import jwt_helper


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


async def create_user(user: user.UserModel):
    user_collection = get_user_collection()
    user.password = jwt_helper.encrypt(user.password)
    new_user = await user_collection.insert_one(user.model_dump(by_alias=True, exclude=["id"]))
    return new_user


async def get_user_by_field(**kwargs):
    user_collection = get_user_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}
    user = await user_collection.find_one(query)
    if not user:
        raise UserNotFoundError("User not found with the provided information.")
    return user


async def update_user(user: user.UserModel):
    user_collection = get_user_collection()
    await user_collection.update_one({"_id": bson.ObjectId(user.id)}, {"$set": user.model_dump(by_alias=True, exclude=["id"])})
    return user
