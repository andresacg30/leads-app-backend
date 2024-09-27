
from fastapi import Body, APIRouter, HTTPException, Request
from passlib.context import CryptContext

import app.controllers.user as user_controller
from app.auth.jwt_handler import sign_jwt, decode_jwt
from app.models.user import UserModel, UserData, UserSignIn, RefreshTokenRequest
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
            tokens = sign_jwt(user_credentials.username, user_exists["permissions"])
            await user_controller.store_refresh_token(user_credentials.username, tokens["refresh_token"])
            return tokens

        raise HTTPException(status_code=403, detail="Incorrect email or password")

    raise HTTPException(status_code=403, detail="Incorrect email or password")


@router.post("/reset-password")
async def reset_password(request: Request, user: UserModel = Body(...)):
    if request.headers.get("x-api-key") != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    try:
        user_exists = await user_controller.get_user_by_field(email=user.email)
    except user_controller.UserNotFoundError:
        user_exists = None
    if not user_exists:
        raise HTTPException(
            status_code=404, detail="user with email supplied does not exist"
        )

    user.password = hash_helper.hash(user.password)
    await user_controller.update_user(user)
    return {"message": "Password reset successful"}


@router.post("/refresh")
async def refresh_token(refresh_request: RefreshTokenRequest = Body(...)):
    try:
        payload = decode_jwt(refresh_request.refresh_token)
        user = await user_controller.get_user_by_field(email=payload["user_id"])
        if user and user["refresh_token"] == refresh_request.refresh_token:
            tokens = sign_jwt(user["email"], user["permissions"])
            await user_controller.store_refresh_token(user["email"], tokens["refresh_token"])
            return tokens
        raise HTTPException(status_code=403, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid refresh token")


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
        "name": user.name,
        "email": user.email
    }
