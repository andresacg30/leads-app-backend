
from fastapi import Body, APIRouter, HTTPException, Request
from passlib.context import CryptContext

import app.controllers.user as user_controller
from app.auth.jwt_handler import sign_jwt
from app.models.user import UserModel, UserData, UserSignIn
from settings import Settings


settings = Settings()

router = APIRouter()

hash_helper = CryptContext(schemes=["bcrypt"])


@router.post("/login")
async def user_login(user_credentials: UserSignIn = Body(...)):
    try:
        user_exists = await user_controller.get_user_by_field(email=user_credentials.username)
    except user_controller.UserNotFoundError:
        user_exists = None
    if user_exists:
        password = hash_helper.verify(user_credentials.password, user_exists["password"])
        if password:
            return sign_jwt(user_credentials.username)

        raise HTTPException(status_code=403, detail="Incorrect email or password")

    raise HTTPException(status_code=403, detail="Incorrect email or password")


@router.post("", response_model=UserData)
async def user_signup(request: Request, user: UserModel = Body(...)):
    if request.headers.get("x-api-key") != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    try:
        user_exists = await user_controller.get_user_by_field(email=user.email)
    except user_controller.UserNotFoundError:
        user_exists = None
    if user_exists:
        raise HTTPException(
            status_code=409, detail="user with email supplied already exists"
        )

    await user_controller.create_user(user)
    return {
        "full_name": user.full_name,
        "email": user.email
    }
