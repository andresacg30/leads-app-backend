import bson

from datetime import datetime
from fastapi import APIRouter, Body, status, HTTPException, Depends, Response

import app.controllers.campaign as campaign_controller
import app.controllers.payment as payment_controller
import app.controllers.transaction as transaction_controller
import app.controllers.order as order_controller
import app.controllers.user as user_controller
import app.integrations.stripe as stripe_controller

from app.auth.jwt_bearer import get_current_user
from app.auth.jwt_handler import create_access_token
from app.models.order import OrderModel
from app.models.payment import PaymentModel, UpdatePaymentModel, PaymentCollection, CheckoutRequest, PaymentTypeRequest
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from main import stripe


router = APIRouter(prefix="/api/payment", tags=["payment"])


@router.post("/get-products")
async def get_products(request: PaymentTypeRequest, user: UserModel = Depends(get_current_user)):
    try:
        campaign_id = bson.ObjectId(request.campaign_id)
        stripe_account_id = await campaign_controller.get_stripe_account_id(campaign_id)
        product_list = await stripe_controller.get_products(
            payment_type=request.payment_type,
            stripe_account_id=stripe_account_id,
            campaign_id=str(campaign_id)
        )
        return product_list
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-customer-portal-session")
async def create_customer_portal_session(campaign_id: str = Body(..., embed=True), user: UserModel = Depends(get_current_user)):
    try:
        stripe_account_id = await campaign_controller.get_stripe_account_id(bson.ObjectId(campaign_id))
        if not user.stripe_customer_ids:
            raise HTTPException(status_code=400, detail="User does not have a stripe customer id")
        session_url = await stripe_controller.create_customer_portal_session(user, campaign_id, stripe_account_id=stripe_account_id)
        return {"url": session_url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-checkout-session")
async def create_checkout_session(request: CheckoutRequest, user: UserModel = Depends(get_current_user)):
    try:
        stripe_account_id = await campaign_controller.get_stripe_account_id(bson.ObjectId(request.campaign_id))
        checkout_session: stripe.checkout.Session = await stripe_controller.create_checkout_session(
            products=request.products,
            payment_type=request.payment_type,
            user=user,
            stripe_account_id=stripe_account_id,
            campaign_id=request.campaign_id
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/verify-session")
async def verify_session(
    session_id: str,
    campaign_id: str,
    payment_type: str,
    products: str = None,
    user: UserModel = Depends(get_current_user)
):
    try:
        if products:
            products = {product.split(":")[0]: product.split(":")[1] for product in products.split(",")}
        stripe_account_id = await campaign_controller.get_stripe_account_id(bson.ObjectId(campaign_id))
        session = await stripe_controller.verify_checkout_session(session_id, stripe_account_id=stripe_account_id)
        if session.payment_status == "paid":
            access_token = None
            if user.is_new_user():
                access_token = await user_controller.change_user_permissions(user.id, new_permissions=['agent'])
            return {"status": "success", "access_token": access_token}
        else:
            return {"status": "pending"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get(
    "/{id}",
    response_description="Get a single payment",
    response_model=PaymentModel,
    response_model_by_alias=False
)
async def show_payment(id: str):
    """
    Get the record for a specific payment, looked up by `id`.
    """
    try:
        payment = await payment_controller.get_payment(id)
        return payment

    except payment_controller.PaymentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Payment {id} not found")


@router.put(
    "/{id}",
    response_description="Update a payment",
    response_model=PaymentModel,
    response_model_by_alias=False
)
async def update_payment(id: str, payment: UpdatePaymentModel = Body(...)):
    """
    Update individual fields of an existing payment record.

    Only the provided fields will be updated.
    Any missing or `null` fields will be ignored.
    """
    try:
        updated_payment = await payment_controller.update_payment(id, payment)
        return {"id": str(updated_payment["_id"])}

    except payment_controller.PaymentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except payment_controller.PaymentIdInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}", response_description="Delete a payment")
async def delete_payment(id: str):
    """
    Remove a single payment record from the database.
    """
    delete_result = await payment_controller.delete_payment(id=id)

    if delete_result.deleted_count == 1:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    raise HTTPException(status_code=404, detail=f"Payment {id} not found")


@router.post(
    "",
    response_description="Add new payment",
    status_code=status.HTTP_201_CREATED,
    response_model_by_alias=False
)
async def create_payment(payment: PaymentModel = Body(...)):
    """
    Insert a new payment record.

    A unique `id` will be created and provided in the response.
    """
    new_payment = await payment_controller.create_payment(payment)
    return {"id": str(new_payment.inserted_id)}


@router.get(
    "",
    response_description="Get all payments",
    response_model=PaymentCollection,
    response_model_by_alias=False
)
async def list_payments(page: int = 1, limit: int = 10):
    """
    List all of the payment data in the database within the specified page and limit.
    """
    payments = await payment_controller.get_all_payments(page=page, limit=limit)
    return PaymentCollection(payments=payments)
