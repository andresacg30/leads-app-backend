import ast
import bson
import datetime
import random
import string
import logging
from fastapi import Body, APIRouter, HTTPException, Request, Depends
from passlib.context import CryptContext

import app.controllers.campaign as campaign_controller
import app.controllers.user as user_controller
import app.background_jobs.user as user_background_jobs
import app.integrations.stripe as stripe_integration

from app.auth.jwt_handler import sign_jwt, decode_jwt
from app.auth.jwt_bearer import get_current_user
from app.background_jobs.job import cancel_job
from app.models.campaign import CampaignModel
from app.models.user import UserSignIn, RefreshTokenRequest, UserModel, UserCollection
from app.tools.constants import OTP_EXPIRATION
from app.tools import emails
from settings import Settings


settings = Settings()

router = APIRouter()

hash_helper = CryptContext(schemes=["bcrypt"])

logger = logging.getLogger(__name__)


@router.get("/get-stripe-account-status")
async def get_stripe_account_status(user: UserModel = Depends(get_current_user)):
    try:
        user_campaign = await campaign_controller.get_one_campaign(user.campaigns[0])
        if not user_campaign:
            return {"status": "inactive"}
        stripe_customer_id = user.stripe_customer_ids.get(user_campaign.id)
        has_last_payment = await stripe_integration.get_last_user_payment(
            stripe_customer_id=stripe_customer_id,
            stripe_account_id=user_campaign.stripe_account_id
        )
        if has_last_payment:
            user.permissions = ["agent"]
            await user_controller.update_user(user)
            return {"status": "active", "permissions": user.permissions}
        return {"status": "inactive"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/onboard-new-campaign")
async def onboard_new_campaign(request: Request, email: str = Body(..., embed=True)):
    print("Onboarding new campaign")
    _, stripe_onboarding_url = await stripe_integration.create_stripe_connect_account(email)
    return stripe_onboarding_url


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
        task_id = cancel_job(user.account_creation_task_id) 
        logger.info(f"User {user.id} has been activated and task {task_id} has been canceled")
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


@router.post("/get-many")
async def get_many_users(request: Request, user_ids: list = Body(...)):
    try:
        users = await user_controller.get_users(user_ids)
        return {"data": list(user.to_json() for user in UserCollection(data=users).data)}
    except user_controller.UserNotFoundError:
        raise HTTPException(status_code=404, detail="Users not found")


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
    user_campaigns = []
    for sign_up_code in user["sign_up_codes"]:
        try:
            campaign = await campaign_controller.get_campaign_by_sign_up_code(sign_up_code)
        except campaign_controller.CampaignNotFoundError:
            raise HTTPException(status_code=404, detail=f"Sign up code {sign_up_code} not found")
        user_campaigns.append(campaign)
    if any(campaign.status != "active" for campaign in user_campaigns):
        raise HTTPException(status_code=404, detail="Campaign is not active")
    created_user = await user_controller.create_user(user)
    await user_background_jobs.add_to_otp_verification_queue(
        created_user
    )
    emails.send_verify_code_email(
        first_name=user["first_name"],
        email=user["email"],
        otp_code=user["otp_code"]
    )
    return {"id": str(created_user.id)}


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


@router.get(
    "",
    response_description="Get all users",
    response_model_by_alias=False
)
async def list_users(page: int = 1, limit: int = 10, sort: str = "name=ASC", filter: str = None, user: UserModel = Depends(get_current_user)):
    """
    List all of the user data in the database within the specified page and limit.
    """
    if sort.split('=')[1] not in ["ASC", "DESC"]:
        raise HTTPException(status_code=400, detail="Invalid sort parameter")
    try:
        filter = ast.literal_eval(filter) if filter else None
        if not user.is_admin():
            if not user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
            filter["campaigns"] = {"$in": [bson.ObjectId(campaign_id) for campaign_id in user.campaigns]}
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        users, total = await user_controller.get_all_users(page=page, limit=limit, sort=sort, filter=filter)
        return {
            "data": list(user.to_json() for user in UserCollection(data=users).data),
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
