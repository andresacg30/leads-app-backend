import bson
import logging
import math
import datetime

from bson import ObjectId
import bson.errors
from pymongo import ReturnDocument
from typing import List, Dict, Optional
from motor.core import AgnosticCollection

from app.db import Database
from app.models.agent import AgentModel
from app.models.campaign import CampaignModel
from app.models.order import OrderModel, UpdateOrderModel
from app.models.user import UserModel
from app.tools import emails, constants


logger = logging.getLogger(__name__)


def get_order_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["order"]


class OrderNotFoundError(Exception):
    pass


class OrderIdInvalidError(Exception):
    pass


async def create_order(order: OrderModel, user: UserModel, products: list = None, leftover_balance: float = 0):
    from app.controllers.campaign import get_one_campaign, get_campaign_agency_users
    from app.controllers.agent import get_agent_by_field, recalculate_daily_limit, update_daily_lead_limit
    agent_in_db = await get_agent_by_field(_id=user.agent_id)
    agent = AgentModel(**agent_in_db)
    order_campaign = await get_one_campaign(str(order.campaign_id))
    order_collection = get_order_collection()
    campaign_last_closed_order = await get_most_recent_closed_order_by_agent_and_campaign(str(user.agent_id), str(order.campaign_id))
    campaign_last_open_order_fresh = await get_oldest_open_order_by_agent_and_campaign(str(user.agent_id), str(order.campaign_id), is_second_chance=False)
    campaign_last_open_order_second_chance = await get_oldest_open_order_by_agent_and_campaign(str(user.agent_id), str(order.campaign_id), is_second_chance=True)
    order = calculate_lead_amounts(order, order_campaign, agent, products)
    if campaign_last_closed_order and not (campaign_last_open_order_fresh or campaign_last_open_order_second_chance):
        added_fresh_leads, added_second_chance_leads = calculate_extra_leads_for_leftover_balance(
            agent=agent,
            order_campaign=order_campaign,
            leftover_balance=leftover_balance,
            order=order
        )
        order.fresh_lead_amount += added_fresh_leads
        order.second_chance_lead_amount += added_second_chance_leads
    created_order = await order_collection.insert_one(
        order.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    if campaign_last_open_order_fresh or campaign_last_open_order_second_chance:
        new_limit = await recalculate_daily_limit(agent=agent, order=order)
        campaign_limit = next(
            (campaign for campaign in agent.daily_lead_limit if campaign.campaign_id == order.campaign_id),
            None
        )
        highest_limit = max(new_limit, campaign_limit.limit)
        agent.daily_lead_limit[agent.daily_lead_limit.index(campaign_limit)].limit = highest_limit
        await update_daily_lead_limit(agent=agent, campaign_id=order.campaign_id, daily_lead_limit=highest_limit)
    else:
        new_limit = await recalculate_daily_limit(agent=agent, order=order)
        higuest_limit = max(new_limit, constants.DEFAULT_LEAD_LIMIT)
        await update_daily_lead_limit(agent=agent, campaign_id=order.campaign_id, daily_lead_limit=higuest_limit)
    campaign_admin_addresses = [user.email for user in await get_campaign_agency_users([order_campaign])]
    order_type = order.type.capitalize().replace("_", " ")
    emails.send_new_order_email(
        emails=campaign_admin_addresses,
        campaign=order_campaign.name,
        type=order_type,
        amount=order.order_total,
        lead_amount=order.fresh_lead_amount,
        second_chance_lead_amount=order.second_chance_lead_amount,
        agent_name=user.name
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


async def get_oldest_open_order_by_agent_and_campaign(
    agent_id: str,
    campaign_id: str,
    is_second_chance: bool = False
) -> Optional[OrderModel]:
    order_collection = get_order_collection()

    pipeline = [
        {
            "$match": {
                "agent_id": ObjectId(agent_id),
                "campaign_id": ObjectId(campaign_id),
                "status": "open"
            }
        },
        # Lookup for how many fresh leads are associated with each order
        {
            "$lookup": {
                "from": "lead",
                "let": {"order_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$lead_order_id", "$$order_id"]
                            }
                        }
                    },
                    {"$count": "fresh_count"}
                ],
                "as": "fresh_leads"
            }
        },
        # Lookup for how many second-chance leads are associated with each order
        {
            "$lookup": {
                "from": "lead",
                "let": {"order_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$second_chance_lead_order_id", "$$order_id"]
                            }
                        }
                    },
                    {"$count": "second_chance_count"}
                ],
                "as": "second_chance_leads"
            }
        },
        {
            "$addFields": {
                "fresh_completed": {
                    "$ifNull": [{"$first": "$fresh_leads.fresh_count"}, 0]
                },
                "second_completed": {
                    "$ifNull": [{"$first": "$second_chance_leads.second_chance_count"}, 0]
                }
            }
        },
        {
            # Only keep orders that haven't fulfilled their needed leads
            "$match": {
                "$expr": {
                    "$cond": {
                        "if": {"$eq": [is_second_chance, True]},
                        "then": {"$lt": ["$second_completed", "$second_chance_lead_amount"]},
                        "else": {"$lt": ["$fresh_completed", "$fresh_lead_amount"]}
                    }
                }
            }
        },
        # Sort by date ascending
        {"$sort": {"date": 1}},
        # Limit to the oldest single match
        {"$limit": 1}
    ]

    docs = await order_collection.aggregate(pipeline).to_list(None)
    return OrderModel(**docs[0]) if docs else None


async def get_most_recent_closed_order_by_agent_and_campaign(agent_id: str, campaign_id: str):
    order_collection = get_order_collection()
    order_in_db = await order_collection.find_one(
        {"agent_id": ObjectId(agent_id), "campaign_id": ObjectId(campaign_id), "status": "closed"}, sort=[("date", -1)]
    )
    order = OrderModel(**order_in_db) if order_in_db else None
    return order


async def get_lead_count(order_id: str):
    from app.controllers.lead import get_lead_collection
    lead_collection = get_lead_collection()
    lead_count = await lead_collection.count_documents({"lead_order_id": ObjectId(order_id)})
    return lead_count


async def get_second_chance_lead_count(order_id: str):
    from app.controllers.lead import get_lead_collection
    lead_collection = get_lead_collection()
    lead_count = await lead_collection.count_documents({"second_chance_lead_order_id": ObjectId(order_id)})
    return lead_count


def determine_distribution_type(order: OrderModel, agent: AgentModel) -> str:
    """Determine distribution type based on order type and lead amounts."""
    if order.type == "one_time":
        if order.fresh_lead_amount > 0 and order.second_chance_lead_amount == 0:
            return "fresh_only"
        elif order.fresh_lead_amount == 0 and order.second_chance_lead_amount > 0:
            return "second_chance_only"
        return "mixed"
    elif order.type == "refund":
        return "fresh_only"
    return agent.distribution_type


def calculate_lead_amounts_by_distribution(
    order_total: float,
    lead_price: float,
    second_chance_lead_price: float,
    distribution_type: str
) -> tuple[int, int]:
    if distribution_type == "fresh_only":
        return math.floor(order_total / lead_price), 0
    elif distribution_type == "second_chance_only":
        return 0, math.floor(order_total / second_chance_lead_price)
    else:  # mixed
        fresh_amount = math.floor((order_total * 0.8) / lead_price)
        second_chance_amount = math.floor((order_total * 0.2) / second_chance_lead_price)
        return fresh_amount, second_chance_amount


def calculate_lead_amounts(order: OrderModel, order_campaign: CampaignModel, agent: AgentModel, products: list = None):
    if products:
        for product in products:
            if product.product_name not in ["Fresh Lead", "Aged Lead", "Second Chance Lead"]:
                raise ValueError("Invalid product type")
            if product.product_name == "Fresh Lead":
                order.fresh_lead_amount = product.quantity
            if product.product_name == "Aged Lead" or product.product_name == "Second Chance Lead":
                order.second_chance_lead_amount = product.quantity
    else:
        lead_price = agent.lead_price_override or order_campaign.price_per_lead
        second_chance_lead_price = agent.second_chance_lead_price_override or order_campaign.price_per_second_chance_lead

        distribution_type = determine_distribution_type(order, agent)
        fresh_amount, second_chance_amount = calculate_lead_amounts_by_distribution(
            order_total=order.order_total,
            lead_price=lead_price,
            second_chance_lead_price=second_chance_lead_price,
            distribution_type=distribution_type
        )

        order.fresh_lead_amount += fresh_amount
        order.second_chance_lead_amount += second_chance_amount
    return order


def calculate_extra_leads_for_leftover_balance(
    agent: AgentModel,
    order_campaign: CampaignModel,
    leftover_balance: float,
    order: OrderModel
) -> tuple[int, int]:
    """Calculate extra leads based on order type and distribution preferences."""
    price_per_lead = agent.lead_price_override or order_campaign.price_per_lead
    price_per_second_chance_lead = (
        agent.second_chance_lead_price_override or
        order_campaign.price_per_second_chance_lead
    )

    distribution_type = determine_distribution_type(order, agent)

    if distribution_type == "fresh_only":
        fresh_leads = math.floor(leftover_balance / price_per_lead)
        return fresh_leads, 0

    if distribution_type == "second_chance_only":
        second_chance_leads = math.floor(leftover_balance / price_per_second_chance_lead)
        return 0, second_chance_leads

    # Mixed distribution
    fresh_leads = 0
    second_chance_leads = 0
    if leftover_balance >= price_per_lead:
        fresh_leads = math.floor(leftover_balance / price_per_lead)
        leftover_balance -= fresh_leads * price_per_lead

    if leftover_balance >= price_per_second_chance_lead:
        second_chance_leads = math.floor(leftover_balance / price_per_second_chance_lead)

    return fresh_leads, second_chance_leads


async def check_order_amounts_and_close(order: OrderModel):
    if await order.fresh_lead_completed >= order.fresh_lead_amount and await order.second_chance_lead_completed >= order.second_chance_lead_amount:
        order.status = "closed"
        order.completed_date = datetime.datetime.utcnow()
        await update_order(str(order.id), order)


async def get_order_metrics(campaigns: List[bson.ObjectId]) -> Dict[str, int]:

    order_collection = get_order_collection()

    pipeline = [
        {
            "$match": {
                "campaign_id": {"$in": campaigns},
                "status": "open"
            }
        },
        {
            "$lookup": {
                "from": "lead",
                "let": {"order_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$lead_order_id", "$$order_id"]
                            }
                        }
                    },
                    {"$count": "fresh_count"}
                ],
                "as": "fresh_leads"
            }
        },
        {
            "$lookup": {
                "from": "lead",
                "let": {"order_id": "$_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$eq": ["$second_chance_lead_order_id", "$$order_id"]
                            }
                        }
                    },
                    {"$count": "second_chance_count"}
                ],
                "as": "second_chance_leads"
            }
        },
        {
            "$group": {
                "_id": None,
                "total_open_orders": {"$sum": 1},
                "fresh_leads_remaining": {
                    "$sum": {
                        "$subtract": [
                            "$fresh_lead_amount",
                            {"$ifNull": [{"$first": "$fresh_leads.fresh_count"}, 0]}
                        ]
                    }
                },
                "second_chance_leads_remaining": {
                    "$sum": {
                        "$subtract": [
                            "$second_chance_lead_amount",
                            {"$ifNull": [{"$first": "$second_chance_leads.second_chance_count"}, 0]}
                        ]
                    }
                }
            }
        }
    ]

    result = await order_collection.aggregate(pipeline).to_list(None)

    return {
        "total_open_orders": result[0].get("total_open_orders", 0) if result else 0,
        "fresh_leads_needed": result[0].get("fresh_leads_remaining", 0) if result else 0,
        "second_chance_leads_needed": result[0].get("second_chance_leads_remaining", 0) if result else 0
    }


async def get_many_orders(ids: List[str], user: UserModel):
    order_collection = get_order_collection()
    orders_in_db = await order_collection.find({"_id": {"$in": [ObjectId(id) for id in ids]}}).to_list(None)
    orders = [OrderModel(**order) for order in orders_in_db]
    return orders
