import datetime
import logging
import app.integrations.stripe as stripe_controller
from bson import ObjectId

from fastapi import APIRouter, Request, HTTPException, Response

from app.models.user import SubscriptionDetailsModel
from app.controllers import user as user_controller
from settings import get_settings
from app.tools.emails import send_error_to_admin, send_cancellation_email_to_agent, send_cancellation_email_to_agency

router = APIRouter(prefix="/api/webhook", tags=["order"])
settings = get_settings()
logger = logging.getLogger(__name__)


@router.post("/create-order-from-stripe-subscription-payment")
async def create_order_from_stripe_subscription_payment_connected_accounts(
    request: Request
):
    """
    Create an order record from a Stripe subscription payment.
    """
    response = await create_order_from_stripe_subscription_payment(request=request, endpoint_secret=settings.stripe_payment_endpoint_secret)
    return response


@router.post("/create-order-from-stripe-subscription-payment-self-account")
async def create_order_from_stripe_subscription_payment_self_account(
    request: Request
):
    """
    Create an order record from a Stripe subscription payment.
    """
    response = await create_order_from_stripe_subscription_payment(request=request, endpoint_secret=settings.stripe_self_account_payment_endpoint_secret)
    return response


@router.post("/cancel-subscription")
async def cancel_subscription(request: Request):
    """
    Cancel a user's subscription.
    """
    response = await cancel_subscription_from_stripe(request=request, endpoint_secret=settings.stripe_cancel_subscription_endpoint_secret)
    return response


@router.post("/cancel-subscription-self-account")
async def cancel_subscription_self_account(request: Request):
    """
    Cancel a user's subscription.
    """
    response = await cancel_subscription_from_stripe(request=request, endpoint_secret=settings.stripe_cancel_subscription_endpoint_secret_self_account)
    return response



async def create_order_from_stripe_subscription_payment(
    request: Request, endpoint_secret
):
    """
    Create an order record from a Stripe subscription payment.
    """
    payload = await request.body()

    sig_header = request.headers.get("stripe-signature")
    event = await stripe_controller.construct_event(
        payload=payload,
        sig_header=sig_header,
        endpoint_secret=endpoint_secret
    )
    if not event:
        raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        payment_intent = event.data.object
        stripe_account = event.account if hasattr(event, "account") else settings.stripe_self_account
        if payment_intent.description == "Subscription update":
            transaction_id, order_id = await stripe_controller.add_transaction_from_new_payment_intent(
                payment_intent_id=payment_intent.id,
                stripe_account_id=stripe_account
            )
            if not transaction_id or not order_id:
                logger.warning(f"Payment received but no user found. Stripe ID: {payment_intent.customer}")
                raise HTTPException(status_code=200, detail="Payment received but no user found")
            logger.info(f"Webhook received, subscription update. Transaction: {transaction_id}. Order: {order_id}")
            return Response(
                content=f"Webhook received: {event['type']}. Transation: {transaction_id}. Order: {order_id}",
                media_type="application/json"
            )
        elif payment_intent.description == "Subscription creation":
            try:
                transaction_id, order_id = await stripe_controller.add_transaction_from_new_payment_intent(
                    payment_intent_id=payment_intent.id,
                    stripe_account_id=stripe_account
                )
                user = await user_controller.get_user_by_stripe_id(payment_intent.customer)
                if not user:
                    logger.warning(f"Payment received but no user found. Stripe ID: {payment_intent.customer}")
                    return Response(content="Webhook received, subscription creation but no user found", media_type="application/json", status_code=200)
                user.has_subscription = True
                new_subscription = SubscriptionDetailsModel(
                    start_date=datetime.datetime.utcnow(),
                    amount_per_week=payment_intent.amount / 100
                )
                user.subscription_details.current_subscriptions.append(new_subscription)
                await user_controller.update_user(user)
                logger.info(f"Webhook received, subscription creation. Transaction: {transaction_id}, Order: {order_id}")
                return Response(content=f"Webhook received, subscription creation. Transaction: {transaction_id}, Order: {order_id} ", media_type="application/json", status_code=200)
            except user_controller.UserNotFoundError:
                logger.warning("Payment received but no user found")
                return Response(content="Webhook received, subscription creation but no user found", media_type="application/json", status_code=200)
        else:
            try:
                transaction_id, order_id = await stripe_controller.add_transaction_from_new_payment_intent(
                    payment_intent_id=payment_intent.id,
                    stripe_account_id=stripe_account
                )
                if not transaction_id or not order_id:
                    logger.warning("Payment received but no user found")
                    raise HTTPException(status_code=200, detail=f"Payment received but no user found. Stripe ID: {payment_intent.customer}")
                logger.info(f"Webhook received: {event['type']}. Transaction: {transaction_id}. Order: {order_id}")
                return Response(
                    content=f"Webhook received: {event['type']}. Transaction: {transaction_id}. Order: {order_id}",
                    media_type="application/json"
                )
            except Exception as e:
                logger.error(f"error: {e}")
                return Response(content=f"error: {e}", media_type="application/json", status_code=200)
    except Exception as e:
        send_error_to_admin(f"Error: {e}. User: {payment_intent.customer}")
        logger.error(f"Error: {e}")
        return Response(content=f"Error: {e}", media_type="application/json", status_code=200)


async def cancel_subscription_from_stripe(request: Request, endpoint_secret):
    """
    Cancel a user's subscription.
    """
    from app.controllers import campaign as campaign_controller
    from app.integrations.stripe import stripe
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = await stripe_controller.construct_event(
        payload=payload,
        sig_header=sig_header,
        endpoint_secret=endpoint_secret
    )
    if not event:
        raise HTTPException(status_code=400, detail="Invalid signature")
    subscription = event.data.object
    if subscription.status == "canceled":
        try:
            user = await user_controller.get_user_by_stripe_id(subscription.customer)
            if not user:
                return Response(content="Webhook received, subscription cancel but no user found", media_type="application/json", status_code=200)
            user.has_subscription = False
            if user.subscription_details.current_subscriptions:
                canceled_subscription = user.subscription_details.current_subscriptions.pop(
                    next(
                        (i for i, sub in enumerate(user.subscription_details.current_subscriptions)
                            if sub.amount_per_week == subscription.plan.amount / 100),
                        -1
                    )
                )
                canceled_subscription.end_date = datetime.datetime.utcnow()
                user.subscription_details.past_subscriptions.append(canceled_subscription)
                await user_controller.update_user(user)
            stripe_account = event.account if hasattr(event, "account") else settings.stripe_self_account
            product = stripe.Product.retrieve(subscription.get("items").get("data")[0].price.product, stripe_account=stripe_account)
            campaign_id = product.metadata["campaign_id"]
            if not campaign_id:
                return Response(content="Webhook received, subscription cancelled but no campaign found", media_type="application/json", status_code=200)
            campaign = await campaign_controller.get_one_campaign(ObjectId(campaign_id))
            send_cancellation_email_to_agent(
                email=user.email,
                user_name=user.name,
                campaign_name=campaign.name,
                amount=canceled_subscription.amount_per_week,
                cancellation_date=canceled_subscription.end_date
            )
            campaign_email_addresses = [user.email for user in await campaign_controller.get_campaign_agency_users(campaigns=[campaign])]
            send_cancellation_email_to_agency(
                emails=campaign_email_addresses,
                user_name=user.name,
                campaign_name=campaign.name,
                amount=canceled_subscription.amount_per_week,
                cancellation_date=canceled_subscription.end_date
            )
            logger.info(f"Webhook received, subscription cancelled for user {user.id}")
            return Response(content="Webhook received, subscription cancelled", media_type="application/json", status_code=200)
        except user_controller.UserNotFoundError:
            logger.warning("Webhook received, subscription cancelled but no user found")
            return Response(content="Webhook received, subscription cancelled but no user found", media_type="application/json", status_code=200)
    logger.warning("Webhook received, not subscription cancelled")
    return Response(content="Webhook received, not subscription cancelled", media_type="application/json", status_code=200)
