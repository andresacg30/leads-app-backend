from bson import ObjectId
from main import stripe
from settings import get_settings
from typing import List

from app.models.payment import ProductSelection
from app.models.user import UserModel
from app.tools import emails


settings = get_settings()


async def create_checkout_session(products: List[ProductSelection], payment_type, user: UserModel):
    line_items = []

    for product in products:
        if payment_type == "recurring":
            prices = stripe.Price.list(
                product=product.product_id,
                active=True,
                type='recurring',
                limit=1
            )
            quantity = 1
        else:
            prices = stripe.Price.list(
                product=product.product_id,
                active=True,
                type='one_time',
                limit=1
            )
            quantity = product.quantity

        if not prices.data:
            raise Exception(f"No active price found for product {product.product_id}")

        price_id = prices.data[0].id

        line_item = {
            "price": price_id,
            "quantity": quantity,
        }

        line_items.append(line_item)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="subscription" if payment_type == "recurring" else "payment",
        success_url=f"{settings.frontend_url}/#/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.frontend_url}/#/cancel",
        customer=user.campaign.stripe_customer_id,
    )

    return checkout_session


async def verify_checkout_session(session_id: str):
    session = stripe.checkout.Session.retrieve(session_id)
    if session.mode == "payment":
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
        charge = stripe.Charge.retrieve(payment_intent.latest_charge)
        emails.send_one_time_purchase_receipt(
            receipt_url=charge.receipt_url,
            email=session.customer_details.email,
            user_name=session.customer_details.name,
            amount=charge.amount / 100,
        )
    return session


async def get_products(payment_type: str):
    stripe_products = stripe.Product.list(active=True, limit=100)
    filtered_products = []

    for product in stripe_products['data']:
        if 'metadata' in product and product['metadata'].get('payment_type') == payment_type:
            filtered_products.append(product)

    return {"data": filtered_products}


async def create_customer_portal_session(user: UserModel):
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/#/"
    )
    return session.url


async def create_stripe_connect_account(email: str):
    account = stripe.Account.create(
        email=email,
        type="standard",
        country='US'
    )
    account_url = stripe.AccountLink.create(
        account=account.id,
        refresh_url=f"{settings.frontend_url}/#/redirecting",
        return_url=f"{settings.frontend_url}/#",
        type='account_onboarding'
    )
    return account, account_url


async def get_stripe_account_status(account_id: ObjectId):
    stripe_account = stripe.Account.retrieve(account_id)
    is_active = stripe_account.charges_enabled and stripe_account.payouts_enabled
    return is_active


async def refresh_stripe_account_onboarding_url(account_id: ObjectId):
    account_url = stripe.AccountLink.create(
        account=account_id,
        refresh_url=f"{settings.frontend_url}/#/redirecting",
        return_url=f"{settings.frontend_url}/#",
        type='account_onboarding'
    )
    return account_url.url
