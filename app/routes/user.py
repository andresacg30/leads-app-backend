import ast
from typing import List
import bson
import datetime
import random
import string
import logging
from fastapi import Body, APIRouter, HTTPException, Request, Depends
from passlib.context import CryptContext
import rq

import app.controllers.campaign as campaign_controller
import app.controllers.user as user_controller
import app.background_jobs.user as user_background_jobs
import app.integrations.stripe as stripe_integration

from app.auth.jwt_handler import sign_jwt, decode_jwt, sign_impersonate_jwt
from app.auth.jwt_bearer import get_current_user
from app.background_jobs.job import cancel_job
from app.models.agent import IntegrationDetailsUpdate
from app.models.campaign import CampaignModel
from app.models.user import UserSignIn, RefreshTokenRequest, UserModel, UserCollection
from app.tools.constants import OTP_EXPIRATION
from app.tools import emails
from settings import Settings


settings = Settings()

router = APIRouter()

hash_helper = CryptContext(schemes=["bcrypt"])

logger = logging.getLogger(__name__)


@router.post(
    "/update-integration-details/{campaign_id}",
    response_description="Update user integration details",
    response_model_by_alias=False
)
async def update_user_integration_details(campaign_id: str, request: IntegrationDetailsUpdate, user: UserModel = Depends(get_current_user)):
    """
    Update the integration details for the user's campaigns.
    """
    if not user.is_admin():
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this campaign")
    if user.is_admin():
        campaigns = await campaign_controller.get_campaign_collection().find().to_list(None)
        campaign_ids = [bson.ObjectId(campaign["_id"]) for campaign in campaigns]
        user.campaigns = campaign_ids
    if bson.ObjectId(campaign_id) not in user.campaigns:
        raise HTTPException(status_code=404, detail="User does not have access to this campaign")
    await user_controller.update_user_integration_details(
        user_id=user.id,
        campaign_id=campaign_id,
        integration_details=request.integration_details,
        crm_name=request.crm_name)
    return {"message": "Integration details updated successfully"}


@router.get(
    "/get-user-integration-details/{campaign_id}",
    response_description="Get user integration details",
    response_model_by_alias=False
)
async def get_user_integration_details(campaign_id: str, user: UserModel = Depends(get_current_user)):
    """
    Get the integration details for the user's campaigns.
    """
    if not user.is_admin():
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this campaign")
    if user.is_admin():
        campaigns = await campaign_controller.get_campaign_collection().find().to_list(None)
        campaign_ids = [bson.ObjectId(campaign["_id"]) for campaign in campaigns]
        user.campaigns = campaign_ids
    integration_details = await user_controller.get_user_integration_details(user_id=user.id, campaign_id=campaign_id)
    return {"data": integration_details}


@router.get(
    "/get-active",
    response_description="Get active agents",
    response_model_by_alias=False
)
async def get_active_agents(user: UserModel = Depends(get_current_user)):
    """
    Get the record for all active agents.
    """
    if not user.is_admin():
        if not user.campaigns:
            raise HTTPException(status_code=404, detail="User does not have access to this campaign")
    if user.is_admin():
        campaigns = await campaign_controller.get_campaign_collection().find().to_list(None)
        campaign_ids = [bson.ObjectId(campaign["_id"]) for campaign in campaigns]
        user.campaigns = campaign_ids
    agents, total = await user_controller.get_active_users(user_campaigns=user.campaigns, user=user)
    return {"data": agents, "total": total}


@router.get("/get-profile")
async def get_user_profile(user: UserModel = Depends(get_current_user)):
    user_data = {
        "first_name": user.name.split(" ")[0],
        "last_name": user.name.split(" ")[1],
        "email": user.email
    }
    return user_data


@router.get("/get-stripe-account-status")
async def get_stripe_account_status(user: UserModel = Depends(get_current_user)):
    try:
        for campaign_id in user.campaigns:
            user_campaign = await campaign_controller.get_one_campaign(campaign_id)
            if not user_campaign:
                return {"status": "inactive"}
            stripe_customer_id = user.stripe_customer_ids.get(str(user_campaign.id))
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
    campaign_names = []
    response = []
    for campaign in user.balance:
        campaign_model = await campaign_controller.get_one_campaign(campaign.campaign_id)
        campaign_names.append(campaign_model.name)
        response.append({
            "campaign_name": campaign_model.name,
            "balance": campaign.balance
        })
    return response


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
        if user.account_creation_task_id:
            try:
                task_id = cancel_job(user.account_creation_task_id) 
                logger.info(f"User {user.id} has been activated and task {task_id} has been canceled")
            except Exception as e:
                task_id = None
                logger.warning(f"User {user.id} has been activated but task {task_id} could not be canceled because {e}")
        emails.send_welcome_email(email=email)
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


@router.post("/impersonate")
async def impersonate_user(request: Request, data: dict = Body(...), current_user: UserModel = Depends(get_current_user)):
    if not (current_user.is_admin() or current_user.is_agency() or current_user.is_agency_admin()):
        raise HTTPException(status_code=403, detail="You do not have permission to impersonate another user")

    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")

    try:
        impersonated_user = await user_controller.get_user(bson.ObjectId(user_id))
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")

    tokens = sign_impersonate_jwt(impersonated_user.email, impersonated_user.permissions)
    return {"token": tokens["access_token"]}


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
            user_exists.refresh_token = tokens["refresh_token"]
            user_exists.last_login = datetime.datetime.utcnow()
            await user_controller.update_user(user_exists)
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


@router.get("/{id}")
async def show_user(id: str, request_user: UserModel = Depends(get_current_user)):
    try:
        if not request_user.is_admin():
            if not request_user.campaigns:
                raise HTTPException(status_code=404, detail="User does not have access to this campaign")
        user = await user_controller.get_user(bson.ObjectId(id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.campaigns = list(filter(lambda campaign: campaign in request_user.campaigns, user.campaigns))
        return user.to_json()
    except user_controller.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


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
        user["email"] = user["email"].lower()
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
        campaigns = await campaign_controller.get_campaigns_by_sign_up_code(sign_up_code)
        if not campaigns:
            raise HTTPException(status_code=404, detail=f"Sign up code {sign_up_code} not found")
        user_campaigns.extend(campaigns)
    if any(campaign.status != "active" for campaign in user_campaigns):
        raise HTTPException(status_code=404, detail="Campaign is not active")
    user["campaigns"] = [campaign.id for campaign in user_campaigns]
    created_user = await user_controller.create_user(user)
    await user_background_jobs.add_to_otp_verification_queue(
        created_user
    )
    emails.send_verify_code_email(
        first_name=user["first_name"],
        email=user["email"],
        otp_code=user["otp_code"]
    )
    campaign_admin_addresses = [user.email for user in await campaign_controller.get_campaign_agency_users(user_campaigns)]
    campaign_name = user_campaigns[0].name if len(user_campaigns) == 1 else ", ".join(campaign.name for campaign in user_campaigns)
    formatted_states = ", ".join(user["states_with_license"])
    emails.send_new_sign_up_email(
        emails=campaign_admin_addresses,
        agent_name=f"{user['first_name']} {user['last_name']}",
        agent_email=user["email"],
        agent_phone=user["phone"],
        agent_states_with_license=formatted_states,
        campaign_name=campaign_name,
        agent_answers=user["custom_campaign_responses"]
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
            if "campaigns" in filter:
                filter["campaigns"] = {"$in": [bson.ObjectId(campaign_id) for campaign_id in filter["campaigns"]]}
            else:
                filter["campaigns"] = {"$in": [bson.ObjectId(campaign_id) for campaign_id in user.campaigns]}
        sort = [sort.split('=')[0], 1 if sort.split('=')[1] == "ASC" else -1]
        users, total = await user_controller.get_all_users(page=page, limit=limit, sort=sort, filter=filter, user=user)
        return {
            "data": list(user.to_json() for user in UserCollection(data=users).data),
            "total": total
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/get-campaign-questions"
)
async def get_questions(request: Request, agency_codes: List[str] = Body(..., embed=True)):
    """
    Get the custom sign up questions for a campaign.
    """
    agency_code = agency_codes[0]
    campaign: CampaignModel = await campaign_controller.get_campaign_by_sign_up_code(agency_code)
    if not campaign:
        logger.warning(f"Campaign with sign up code {agency_code} not found", extra={'function': 'get_questions'})
        raise HTTPException(status_code=404, detail="Campaign not found")
    questions = [question for question in campaign.custom_sign_up_questions if question]
    return {"questions": questions}
