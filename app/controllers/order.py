import bson
import logging
import math

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from motor.core import AgnosticCollection

from app.db import Database
from app.models.agent import AgentModel
from app.models.campaign import CampaignModel
from app.models.order import OrderModel, UpdateOrderModel
from app.models.user import UserModel


logger = logging.getLogger(__name__)


def get_order_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["order"]


class OrderNotFoundError(Exception):
    pass


class OrderIdInvalidError(Exception):
    pass


async def create_order(order: OrderModel, user: UserModel, products: list = None):
    from app.controllers.campaign import get_one_campaign
    from app.controllers.agent import get_agent_by_field
    agent_in_db = await get_agent_by_field(_id=user.agent_id)
    agent = AgentModel(**agent_in_db)
    order_campaign = await get_one_campaign(str(order.campaign_id))
    order_collection = get_order_collection()
    order = calculate_lead_amounts(order, order_campaign, agent, products)
    created_order = await order_collection.insert_one(
        order.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    return created_order


async def get_all_orders(page, limit, sort, filter):
    if "id" in filter:
        filter = {"_id": {"$in": [ObjectId(id) for id in filter["id"]]}}
    order_collection = get_order_collection()
    orders = await order_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
    if filter:
        total = await order_collection.count_documents(filter)
    else:
        total = await order_collection.count_documents({})
    return orders, total


async def get_one_order(id):
    order_collection = get_order_collection()
    if (
        order_in_db := await order_collection.find_one({"_id": ObjectId(id)})
    ) is not None:
        order_result = OrderModel(**order_in_db)
        return order_result

    raise OrderNotFoundError(f"Campaign with id {id} not found")


async def update_order(id, order: UpdateOrderModel):
    order_collection = get_order_collection()
    try:
        order = {k: v for k, v in order.model_dump(by_alias=True, mode="python").items() if v is not None}

        if len(order) >= 1:
            update_result = await order_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": order},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                return update_result

            else:
                raise OrderNotFoundError(f"Order with id {id} not found")

        if (existing_order := await order_collection.find_one({"_id": id})) is not None:
            return existing_order
    except bson.errors.InvalidId:
        raise OrderIdInvalidError(f"Invalid id {id} on update order route.")


async def delete_order(id):
    order_collection = get_order_collection()
    try:
        result = await order_collection.delete_one({"_id": ObjectId(id)})
        return result
    except bson.errors.InvalidId:
        raise OrderIdInvalidError(f"Invalid id {id} on delete order route.")


async def get_oldest_open_order_by_agent(agent_id: str):
    order_collection = get_order_collection()
    order_in_db = await order_collection.find_one(
        {"agent_id": ObjectId(agent_id), "status": "open"}, sort=[("date", 1)]
    )
    order = OrderModel(**order_in_db) if order_in_db else None
    return order


async def get_oldest_open_order_by_agent_and_campaign(agent_id: str, campaign_id: str):
    order_collection = get_order_collection()
    order_in_db = await order_collection.find_one(
        {"agent_id": ObjectId(agent_id), "campaign_id": ObjectId(campaign_id), "status": "open"}, sort=[("date", 1)]
    )
    order = OrderModel(**order_in_db) if order_in_db else None
    return order


def calculate_lead_amounts(order: OrderModel, order_campaign: CampaignModel, agent: AgentModel, products: list = None):
    if products:
        for product in products:
            if product.product_name not in ["Fresh Lead", "Aged Lead"]:
                raise ValueError("Invalid product type")
            if product.product_name == "Fresh Lead":
                order.fresh_lead_amount = product.quantity
            if product.product_name == "Aged Lead":
                order.second_chance_lead_amount = product.quantity
    else:
        if agent.lead_price_override:
            lead_price = agent.lead_price_override
        else:
            lead_price = order_campaign.price_per_lead
        if agent.second_chance_lead_price_override:
            second_chance_lead_price = agent.second_chance_lead_price_override
        else:
            second_chance_lead_price = order_campaign.price_per_second_chance_lead
        order.fresh_lead_amount = math.floor((order.order_total * 0.8) / lead_price)
        order.second_chance_lead_amount = math.floor((order.order_total * 0.2) / second_chance_lead_price)
    return order
