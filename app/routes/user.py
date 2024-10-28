import datetime
import random
import string
import logging
from fastapi import Body, APIRouter, HTTPException, Request, Depends
from passlib.context import CryptContext

import app.controllers.user as user_controller

from app.auth.jwt_handler import sign_jwt, decode_jwt
from app.auth.jwt_bearer import get_current_user
from app.models.user import UserSignIn, RefreshTokenRequest, UserModel
from app.tools.constants import OTP_EXPIRATION
from app.tools import emails
from settings import Settings


settings = Settings()

router = APIRouter()

hash_helper = CryptContext(schemes=["bcrypt"])

logger = logging.getLogger(__name__)


@router.get("/get-current-balance")
async def get_user_balance(user: UserModel = Depends(get_current_user)):
    user = await user_controller.get_user_by_field(email=user.email)
    return {"balance": user.balance}


@router.post("/verify-otp")
async def verify_otp(request: Request, email: str = Body(...), otp: str = Body(...)):
    try:
        user = await user_controller.get_user_by_field(email=email)
    except user_controller.UserNotFoundError:
        logging.warning(f"User with email {email} not found", extra={'function': 'verify_otp'})
        return {"message": "OTP code sent"}
    if user.otp_expiration < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="OTP code has expired")
    if user.otp_code == otp:
        await user_controller.activate_user(email)
        return {"message": "OTP confirmed"}
    raise HTTPException(status_code=403, detail="Invalid OTP code")


@router.post("/resend-otp")
async def resend_otp(request: Request, email: str = Body(..., embed=True)):
    try:
        user = await user_controller.get_user_by_field(email=email)
    except user_controller.UserNotFoundError:
        logging.warning(f"User with email {email} not found", extra={'function': 'resend_otp'})
        return {"message": "OTP code sent"}
    user.otp_code = _create_otp_code()
    user.otp_expiration = datetime.datetime.utcnow() + datetime.timedelta(seconds=OTP_EXPIRATION)
    await user_controller.update_user(user)
    emails.send_verify_code_email(
        email=email,
        otp_code=user.otp_code,
        first_name=user.name.split(" ")[0]
    )
    return {"message": "OTP code resent successfully"}


@router.post("/login")
async def user_login(user_credentials: UserSignIn = Body(...)):
    if user_credentials.otp:
        tokens = await _login_with_otp(user_credentials)
        return tokens
    try:
        user_exists = await user_controller.get_user_by_field(email=user_credentials.username)
    except user_controller.UserNotFoundError:
        user_exists = None

    if user_exists:
        if not user_exists.is_email_verified():
            raise HTTPException(status_code=403, detail="User account is not active")
        password = hash_helper.verify(user_credentials.password, user_exists.password)
        if password:
            tokens = sign_jwt(user_credentials.username, user_exists.permissions)
            await user_controller.store_refresh_token(user_credentials.username, tokens["refresh_token"])
            return tokens

        raise HTTPException(status_code=403, detail="Incorrect email or password")

    raise HTTPException(status_code=403, detail="Incorrect email or password")


@router.post("/reset-password-otp")
async def reset_password_otp(request: Request, email: str = Body(..., embed=True)):
    try:
        user_exists = await user_controller.get_user_by_field(email=email)
    except user_controller.UserNotFoundError:
        user_exists = None
    if not user_exists:
        logging.warning(f"User with email {email} not found", function="reset_password_otp")
        return {"message": "Password reset code sent successfully"}

    user_exists.otp_code = _create_otp_code()
    user_exists.otp_expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
    await user_controller.update_user(user_exists)
    emails.send_verify_code_email(
        email=email,
        otp_code=user_exists.otp_code,
        first_name=user_exists.name.split(" ")[0]
    )
    return {"message": "Password reset code sent successfully"}


@router.post("/update-password")
async def update_password(request: Request, email: str = Body(...), newPassword: str = Body(...)):
    try:
        user = await user_controller.get_user_by_field(email=email)
    except user_controller.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp_expiration < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="OTP code has expired")
    user.password = hash_helper.hash(newPassword)
    await user_controller.update_user(user)
    return {"message": "Password reset successfully"}


@router.post("/refresh")
async def refresh_token(refresh_request: RefreshTokenRequest = Body(...)):
    try:
        payload = decode_jwt(refresh_request.refresh_token)
        user = await user_controller.get_user_by_field(email=payload["user_id"])
        if user and user.refresh_token == refresh_request.refresh_token:
            tokens = sign_jwt(user.email, user.permissions)
            await user_controller.store_refresh_token(user.email, tokens["refresh_token"])
            return tokens
        raise HTTPException(status_code=403, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=403, detail="Invalid refresh token")


@router.post("")
async def user_signup(request: Request, user=Body(...)):
    try:
        user_exists = await user_controller.get_user_by_field(email=user["email"])
    except user_controller.UserNotFoundError:
        user_exists = None
    if user_exists:
        raise HTTPException(
            status_code=409, detail="user with email supplied already exists"
        )
    user["otp_code"] = _create_otp_code()
    created_user = await user_controller.create_user(user)
    emails.send_verify_code_email(
        first_name=user["first_name"],
        email=user["email"],
        otp_code=user["otp_code"]
    )
    return {"id": str(created_user.inserted_id)}


def _create_otp_code():
    return ''.join(random.choices(string.digits, k=6))


async def _login_with_otp(user_credentials: UserSignIn):
    try:
        user = await user_controller.get_user_by_field(email=user_credentials.username)
    except user_controller.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    if user.otp_expiration < datetime.datetime.utcnow():
        raise HTTPException(status_code=403, detail="OTP code has expired")
    if user.otp_code == user_credentials.otp:
        tokens = sign_jwt(user_credentials.username, user.permissions)
        await user_controller.store_refresh_token(user_credentials.username, tokens["refresh_token"])
        return tokens
    else:
        raise HTTPException(status_code=403, detail="Invalid OTP code")
