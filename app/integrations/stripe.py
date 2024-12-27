import json
from bson import ObjectId
import urllib.parse
from app.models.campaign import CampaignModel
from main import stripe
from settings import get_settings
from typing import List

from app.controllers import campaign as campaign_controller
from app.controllers import order as order_controller
from app.controllers import transaction as transaction_controller
from app.controllers import user as user_controller
from app.models.transaction import TransactionModel
from app.models.order import OrderModel
from app.models.payment import ProductSelection, PurchasedProduct
from app.models.user import UserModel
from app.tools import emails


settings = get_settings()


async def create_checkout_session(
    products: List[ProductSelection],
    payment_type: str,
    user: UserModel,
    stripe_account_id: str,
    campaign_id: str
):
    line_items = []
    stripe_product_names = {}
    payment_intent_product_info = {}

    for product in products:
        if payment_type == "recurring":
            prices = stripe.Price.list(
                product=product.product_id,
                active=True,
                limit=1,
                stripe_account=stripe_account_id
            )
            quantity = 1
        else:
            prices = stripe.Price.list(
                product=product.product_id,
                active=True,
                limit=1,
                stripe_account=stripe_account_id
            )
            quantity = product.quantity

        if not prices.data:
            raise Exception(f"No active price found for product {product.product_id}")

        price_id = prices.data[0].id
        line_items.append({
            "price": price_id,
            "quantity": quantity,
        })

        stripe_product = stripe.Product.retrieve(
            product.product_id,
            stripe_account=stripe_account_id
        )
        stripe_product_names[stripe_product.name] = quantity
        payment_intent_product_info[stripe_product.id] = quantity

    query_params = {
        "session_id": "{CHECKOUT_SESSION_ID}",
        "campaign_id": campaign_id,
        "payment_type": payment_type
    }

    if payment_type == "one_time" and stripe_product_names:
        products_string = ",".join(
            [f"{name}:{quantity}" for name, quantity in stripe_product_names.items()]
        )
        query_params["products"] = products_string

    encoded_params = urllib.parse.urlencode(query_params, safe='{}')

    success_url = f"{settings.frontend_url}/#/success?{encoded_params}"

    if payment_type == "one_time":
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="subscription" if payment_type == "recurring" else "payment",
            success_url=success_url,
            cancel_url=f"{settings.frontend_url}/#/",
            customer=user.stripe_customer_ids.get(campaign_id),
            stripe_account=stripe_account_id,
            consent_collection={"terms_of_service": "required"},
            payment_intent_data={
                "metadata": {
                    "campaign_id": campaign_id,
                    "products": json.dumps(payment_intent_product_info), 
                }
            }
        )
    else:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=line_items,
            mode="subscription" if payment_type == "recurring" else "payment",
            success_url=success_url,
            cancel_url=f"{settings.frontend_url}/#/",
            customer=user.stripe_customer_ids.get(campaign_id),
            stripe_account=stripe_account_id,
            consent_collection={"terms_of_service": "required"}
        )

    return checkout_session


async def verify_checkout_session(session_id: str, stripe_account_id: str):
    session = stripe.checkout.Session.retrieve(session_id, stripe_account=stripe_account_id)
    if session.mode == "payment" and session.payment_status == "paid":
        payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent, stripe_account=stripe_account_id)
        charge = stripe.Charge.retrieve(payment_intent.latest_charge, stripe_account=stripe_account_id)
        emails.send_one_time_purchase_receipt(
            receipt_url=charge.receipt_url,
            email=session.customer_details.email,
            user_name=session.customer_details.name,
            amount=charge.amount / 100
        )
    return session


async def get_products(payment_type: str, stripe_account_id: str):
    stripe_products = stripe.Product.list(active=True, limit=100, stripe_account=stripe_account_id)
    filtered_products = []

    for product in stripe_products['data']:
        if 'metadata' in product and product['metadata'].get('payment_type') == payment_type:
            filtered_products.append(product)

    filtered_products.sort(key=lambda product: _extract_amount(product['name']))

    return {"data": filtered_products}


async def create_customer_portal_session(user: UserModel, campaign_id, stripe_account_id: str):
    stripe_customer_id = user.stripe_customer_ids[campaign_id]
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{settings.frontend_url}/#/",
        stripe_account=stripe_account_id
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


async def create_customer(user: UserModel, stripe_account_id: str):
    stripe_customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        phone=user.phone,
        stripe_account=stripe_account_id
    )

    return stripe_customer


async def get_last_user_payment(stripe_customer_id: str, stripe_account_id: str):
    payment = stripe.PaymentIntent.list(customer=stripe_customer_id, limit=1, stripe_account=stripe_account_id)
    return payment


async def update_one_time_product_price(product_id: str, price: int, stripe_account_id: str):
    decimal_price = int(price * 100)
    price_list = stripe.Price.list(
        product=product_id,
        active=True,
        type='one_time',
        limit=1,
        stripe_account=stripe_account_id
    )

    new_price = stripe.Price.create(
        unit_amount=decimal_price,
        currency='usd',
        product=product_id,
        stripe_account=stripe_account_id,
        active=True,
        metadata={"payment_type": "one_time"}
    )

    stripe.Product.modify(
        product_id,
        default_price=new_price.id,
        stripe_account=stripe_account_id
    )

    if price_list.data:
        old_price_id = price_list.data[0].id
        stripe.Price.modify(
            old_price_id,
            active=False,
            stripe_account=stripe_account_id
        )

    return new_price.id


def _extract_amount(product_name):
    product_name = product_name.strip()
    amount_str = product_name.split('/')[0].replace('$', '').replace(',', '')
    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0
    return amount


async def add_transaction_from_new_payment_intent(payment_intent_id: str, stripe_account_id: str):
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id, stripe_account=stripe_account_id)
    customer = stripe.Customer.retrieve(payment_intent.customer, stripe_account=stripe_account_id)
    products = []
    try:
        user = await user_controller.get_user_by_email(customer.email)
    except user_controller.UserNotFoundError:
        return None, None
    if payment_intent.invoice:
        order_type = "recurring"
    else:
        products_metadata = payment_intent.metadata.get("products")
        if not products_metadata:
            return None, None
        product_info = json.loads(products_metadata)
        for product_id, quantity in product_info.items():
            prod = stripe.Product.retrieve(product_id, stripe_account=stripe_account_id)
            products.append(PurchasedProduct(product_id=prod.id, product_name=prod.name, quantity=quantity))
        order_type = "one_time"
    campaign_id = await campaign_controller.get_campaign_id_by_stripe_account_id(stripe_account_id)
    current_user_balance = await user_controller.get_user_balance_by_agent_id(user.agent_id)
    created_transaction = await transaction_controller.create_transaction(
        TransactionModel(
            amount=payment_intent.amount / 100,
            campaign_id=campaign_id,
            user_id=user.id,
            payment_intent_id=payment_intent_id,
            date=payment_intent.created,
            type="credit"
        )
    )

    created_order = await order_controller.create_order(
        OrderModel(
            agent_id=user.agent_id,
            campaign_id=campaign_id,
            order_total=payment_intent.amount / 100,
            status="open",
            type=order_type,
        ),
        user,
        products=products or None,
        leftover_balance=current_user_balance
    )

    return created_transaction.inserted_id, created_order.inserted_id


async def construct_event(payload, sig_header, endpoint_secret):
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Error verifying webhook signature: {str(e)}")
        return None


async def get_user_subscriptions(user: UserModel, campaign: CampaignModel):
    subscriptions = stripe.Subscription.list(
        customer=user.stripe_customer_ids[campaign.id],
        stripe_account=campaign.stripe_account_id
    )
    if not subscriptions:
        return []
    return subscriptions.data


async def delete_customer(user: UserModel, campaign: CampaignModel):
    stripe.Customer.delete(
        user.stripe_customer_ids[campaign.id],
        stripe_account=campaign.stripe_account_id
    )
    return True
