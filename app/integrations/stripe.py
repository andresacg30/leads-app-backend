from app.tools.mappings import PRODUCT_PRICE_MAPPING
from main import stripe
from settings import get_settings
from typing import List

from app.models.payment import ProductSelection


settings = get_settings()


async def create_checkout_session(products: List[ProductSelection], payment_type, user):
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
        customer=user.stripe_customer_id,
    )

    return checkout_session


async def verify_checkout_session(session_id: str):
    session = stripe.checkout.Session.retrieve(session_id)
    return session


async def get_products(payment_type: str):
    stripe_products = stripe.Product.list(active=True, limit=100)
    filtered_products = []

    for product in stripe_products['data']:
        if 'metadata' in product and product['metadata'].get('payment_type') == payment_type:
            filtered_products.append(product)

    return {"data": filtered_products}
