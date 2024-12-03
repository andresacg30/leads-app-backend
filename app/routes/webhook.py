import app.integrations.stripe as stripe_controller

from fastapi import APIRouter, Request, HTTPException, Response

from app.auth.jwt_bearer import get_current_user
from settings import get_settings


router = APIRouter(prefix="/api/webhook", tags=["order"])
settings = get_settings()


@router.post("/create-order-from-stripe-subscription-payment")
async def create_order_from_stripe_subscription_payment(
    request: Request
):
    """
    Create an order record from a Stripe subscription payment.
    """
    payload = await request.body()

    sig_header = request.headers.get("stripe-signature")
    event = await stripe_controller.construct_event(
        payload=payload,
        sig_header=sig_header,
        endpoint_secret=settings.stripe_payment_endpoint_secret
    )
    if not event:
        raise HTTPException(status_code=400, detail="Invalid signature")
    payment_intent = event.data.object
    stripe_account = event.account
    if payment_intent.description != "Subscription creation":
        return Response(content="Webhook received, not subscription payment", media_type="application/json", status_code=200)
    transaction_id, order_id = await stripe_controller.add_transaction_from_new_payment_intent(
        payment_intent_id=payment_intent.id,
        stripe_account_id=stripe_account
    )
    if not transaction_id or not order_id:
        raise HTTPException(status_code=200, detail="Payment received but no user found")
    return Response(
        content=f"Webhook received: {event['type']}. Transation: {transaction_id}. Order: {order_id}",
        media_type="application/json"
    )
