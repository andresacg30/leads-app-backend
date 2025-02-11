import bson
import logging
import random
from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import ReturnDocument
from motor.core import AgnosticCollection


from app.db import Database
from app.integrations import crm_chooser
from app.background_jobs import lead as lead_background_jobs
from app.models import lead as lead_model
from app.models.agent import AgentModel
from app.models.campaign import CampaignModel
from app.models.transaction import TransactionModel
from app.models.user import UserModel
from app.tools import formatters as formatter
from app.tools import constants
from app.tools import validators as validator


logger = logging.getLogger(__name__)


class DateField(Enum):
    CREATED = "created_time"
    SOLD = "lead_sold_time"
    SECOND_CHANCE_SOLD = "second_chance_lead_sold_time"


def get_lead_collection() -> AgnosticCollection:
    db = Database.get_db()
    return db["lead"]


class LeadNotFoundError(Exception):
    pass


class LeadIdInvalidError(Exception):
    pass


class LeadEmptyError(Exception):
    pass


async def update_lead(id, lead: lead_model.UpdateLeadModel):
    from app.controllers.order import get_oldest_open_order_by_agent_and_campaign, check_order_amounts_and_close
    from app.controllers.campaign import get_one_campaign
    from app.controllers.user import get_user_by_field, UserNotFoundError
    from app.controllers.transaction import create_transaction
    if all(v is None for v in lead.model_dump(mode="python").values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True, mode="python").items() if v is not None}
        if lead["campaign_id"] in constants.OG_CAMPAIGNS:
            datetime_fields = ["created_time", "lead_sold_time", "second_chance_lead_sold_time", "lead_sold_by_agent_time"]
            if any(field in lead for field in datetime_fields):
                for field in datetime_fields:
                    if field in lead:
                        lead[field] = formatter.format_string_to_utc_datetime(lead[field])
        ### TEMPORAL FOR OG CAMPAIGNS ###
        if lead.get("buyer_id"):
            agent_oldest_open_order = await get_oldest_open_order_by_agent_and_campaign(
                agent_id=lead["buyer_id"],
                campaign_id=lead["campaign_id"],
                is_second_chance=False
            )
            if agent_oldest_open_order:
                lead["lead_order_id"] = agent_oldest_open_order.id
        if lead.get("second_chance_buyer_id"):
            agent_oldest_open_order = await get_oldest_open_order_by_agent_and_campaign(
                agent_id=lead["second_chance_buyer_id"],
                campaign_id=lead["campaign_id"],
                is_second_chance=True
            )
            if agent_oldest_open_order:
                lead["second_chance_lead_order_id"] = agent_oldest_open_order.id
        ### END TEMPORAL FOR OG CAMPAIGNS ###
        if len(lead) >= 1:
            update_result = await lead_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": lead},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                ### TEMPORAL FOR OG CAMPAIGNS ###
                if "buyer_id" in lead or "second_chance_buyer_id" in lead:
                    if str(update_result["campaign_id"]) in constants.OG_CAMPAIGNS:
                        if agent_oldest_open_order:
                            await check_order_amounts_and_close(agent_oldest_open_order)
                        campaign = await get_one_campaign(str(update_result["campaign_id"]))
                        if "buyer_id" in lead and lead["buyer_id"]:
                            try:
                                user = await get_user_by_field(agent_id=lead["buyer_id"])
                                if user:
                                    await create_transaction(
                                        TransactionModel(
                                            user_id=user.id,
                                            amount=-campaign.price_per_lead,
                                            description="Fresh Lead sent",
                                            type="debit",
                                            date=datetime.utcnow(),
                                            lead_id=ObjectId(id),
                                            campaign_id=lead.get("campaign_id"))
                                        )
                            except UserNotFoundError:
                                pass
                        if "second_chance_buyer_id" in lead and lead["second_chance_buyer_id"]:
                            try:
                                user = await get_user_by_field(agent_id=lead["second_chance_buyer_id"])
                                if user:
                                    await create_transaction(
                                        TransactionModel(
                                            user_id=user.id,
                                            amount=-campaign.price_per_second_chance_lead,
                                            description="Second Chance Lead purchase",
                                            type="debit",
                                            date=datetime.utcnow(),
                                            lead_id=ObjectId(id),
                                            campaign_id=lead.get("campaign_id")
                                        )
                                    )
                            except UserNotFoundError:
                                pass
                ### END TEMPORAL FOR OG CAMPAIGNS ###
                return update_result

            else:
                raise LeadNotFoundError(f"Lead with id {id} not found")

        if (existing_lead := await lead_collection.find_one({"_id": id})) is not None:
            return existing_lead
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on update lead route")
    except Exception as e:
        logger.error(f"Error updating lead {id}: {str(e)} . Lead info: {lead}")
        raise Exception("Error")


async def update_lead_from_ghl(id, lead: lead_model.UpdateLeadModel):
    if all(v is None for v in lead.model_dump(mode="python").values()):
        raise LeadEmptyError("No values to update")
    lead_collection = get_lead_collection()
    try:
        lead = {k: v for k, v in lead.model_dump(by_alias=True, mode="python").items() if v is not None}
        if "created_time" in lead:
            lead["created_time"] = formatter.format_time(lead["created_time"])
        if len(lead) >= 1:
            update_result = await lead_collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {"$set": lead},
                return_document=ReturnDocument.AFTER,
            )

            if update_result is not None:
                return update_result

            else:
                raise LeadNotFoundError(f"Lead with id {id} not found")

        if (existing_lead := await lead_collection.find_one({"_id": id})) is not None:
            return existing_lead
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on update lead route")


async def get_lead_by_field(**kwargs):
    from app.controllers import agent as agent_controller
    lead_collection = get_lead_collection()
    query = {k: v for k, v in kwargs.items() if v is not None}
    if "buyer_name" in query:
        try:
            buyer_id = await agent_controller.get_agent_by_field(full_name=query.pop("buyer_name"))
            query["buyer_id"] = buyer_id["_id"]
        except agent_controller.AgentNotFoundError as e:
            raise LeadNotFoundError(str(e))
    if "second_chance_buyer_name" in query:
        try:
            second_chance_buyer_id = await agent_controller.get_agent_by_field(full_name=query.pop("second_chance_buyer_name"))
            query["second_chance_buyer_id"] = second_chance_buyer_id["_id"]
        except agent_controller.AgentNotFoundError as e:
            raise LeadNotFoundError(str(e))
    lead = await lead_collection.find_one(query, sort=[("created_time", -1)])
    if not lead:
        raise LeadNotFoundError("Lead not found with the provided information.")

    return lead


async def create_lead(lead: lead_model.LeadModel):
    lead_collection = get_lead_collection()
    is_valid, rejection_reasons = await validate_lead(lead)
    if not is_valid:
        lead.custom_fields["rejection_reasons"] = rejection_reasons
        lead.custom_fields["invalid"] = "yes"
    else:
        lead.custom_fields["invalid"] = "no"
    new_lead = await lead_collection.insert_one(
        lead.model_dump(by_alias=True, exclude=["id"], mode="python")
    )
    if lead.custom_fields.get("invalid") == "yes":
        return new_lead
    if str(lead.campaign_id) not in constants.OG_CAMPAIGNS:
        if not lead.second_chance_buyer_id:
            if not lead.custom_fields.get("invalid") or lead.custom_fields.get("invalid") == "no":
                lead_background_jobs.process_lead(lead, lead_id=new_lead.inserted_id)
                await lead_background_jobs.schedule_for_second_chance(
                    lead=lead,
                    lead_id=new_lead.inserted_id,
                    time=constants.TIME_FOR_SECOND_CHANCE
                )
    return new_lead


async def get_all_leads(page, limit, sort, filter):
    if not filter:
        filter = {}

    filter = build_query_filters(filter)
    filter, date_gte, date_lte = _handle_lead_received_date_filter(filter)

    if "first_name" in filter:
        filter["first_name"] = {"$regex": str.capitalize(filter["first_name"]), "$options": "i"}
    if "last_name" in filter:
        filter["last_name"] = {"$regex": str.capitalize(filter["last_name"]), "$options": "i"}
    if "agent_id" in filter:
        if not filter["agent_id"]:
            return [], 0
        agent_id = filter.pop("agent_id")
        filter["$or"] = [
            {"buyer_id": ObjectId(agent_id)},
            {"second_chance_buyer_id": ObjectId(agent_id)}
        ]
        pipeline = _build_aggregation_pipeline(filter, sort, page, limit, agent_id, date_gte, date_lte)
    else:
        pipeline = []

    lead_collection = get_lead_collection()
    if pipeline:
        result = await lead_collection.aggregate(pipeline).to_list(None)
        leads = result[0]["data"]
        total = result[0]["total"][0]["count"] if result[0]["total"] else 0
    else:
        leads_in_db = await lead_collection.find(filter).sort([sort]).skip((page - 1) * limit).limit(limit).to_list(limit)
        leads = [lead_model.LeadModel(**lead).to_json() for lead in leads_in_db]
        total = await lead_collection.count_documents(filter) if filter else await lead_collection.count_documents({})

    return leads, total


async def get_one_lead(id):
    lead_collection = get_lead_collection()
    try:
        if (
            lead_in_db := await lead_collection.find_one({"_id": ObjectId(id)})
        ) is not None:
            lead = lead_model.LeadModel(**lead_in_db)
            return lead

        raise LeadNotFoundError(f"Lead with id {id} not found")
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on lead get one route")


async def delete_lead(id):
    lead_collection = get_lead_collection()
    try:
        delete_result = await lead_collection.delete_one({"_id": ObjectId(id)})
        return delete_result
    except bson.errors.InvalidId:
        raise LeadIdInvalidError(f"Invalid id {id} on delete lead route")


async def delete_leads(ids):
    lead_collection = get_lead_collection()
    result = await lead_collection.delete_many({"_id": {"$in": [ObjectId(id) for id in ids if id != "null"]}})
    return result


def _format_created_time_filter(filter):
    if "created_time_gte" in filter or "created_time_lte" in filter:
        filter["created_time"] = {}
    if "created_time_gte" in filter:
        filter["created_time"]["$gte"] = datetime.strptime(filter.pop("created_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "created_time_lte" in filter:
        filter["created_time"]["$lte"] = datetime.strptime(filter.pop("created_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter


def _format_lead_sold_time_filter(filter):
    if "lead_sold_time_gte" in filter or "lead_sold_time_lte" in filter:
        filter["lead_sold_time"] = {}
    if "lead_sold_time_gte" in filter:
        filter["lead_sold_time"]["$gte"] = datetime.strptime(filter.pop("lead_sold_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "lead_sold_time_lte" in filter:
        filter["lead_sold_time"]["$lte"] = datetime.strptime(filter.pop("lead_sold_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter


def _format_second_chance_lead_sold_time_filter(filter):
    if "second_chance_lead_sold_time_gte" in filter or "second_chance_lead_sold_time_lte" in filter:
        filter["second_chance_lead_sold_time"] = {}
    if "second_chance_lead_sold_time_gte" in filter:
        filter["second_chance_lead_sold_time"]["$gte"] = datetime.strptime(filter.pop("second_chance_lead_sold_time_gte"), "%Y-%m-%dT%H:%M:%S.%fZ")
    if "second_chance_lead_sold_time_lte" in filter:
        filter["second_chance_lead_sold_time"]["$lte"] = datetime.strptime(filter.pop("second_chance_lead_sold_time_lte"), "%Y-%m-%dT%H:%M:%S.%fZ")

    return filter


def build_query_filters(filter):
    if "custom_fields" in filter and isinstance(filter["custom_fields"], dict):
        nested_dict = filter.pop("custom_fields")
        for key, val in nested_dict.items():
            if key == "invalid" and val == "no":
                filter["$or"] = [
                    {"custom_fields.invalid": "no"},
                    {"custom_fields.invalid": {"$exists": False}}
                ]
            else:
                filter[f"custom_fields.{key}"] = val
    if "q" in filter:
        query_value = filter["q"]
        query_filters = [
            {"first_name": {"$regex": query_value, "$options": "i"}},
            {"last_name": {"$regex": query_value, "$options": "i"}},
            {"email": {"$regex": query_value, "$options": "i"}},
            {"phone": {"$regex": query_value, "$options": "i"}}
        ]
        if filter.get("$or"):
            filter["$and"] = [{"$or": query_filters}, {"$or": filter.pop("$or")}]
        else:
            filter["$or"] = query_filters
        filter.pop("q")
    if "buyer_id" in filter and filter["buyer_id"]:
        buyer_ids = filter["buyer_id"] if isinstance(filter["buyer_id"], list) else [filter["buyer_id"]]
        filter["buyer_id"] = {"$in": [ObjectId(agent_id) for agent_id in buyer_ids]}

    if "second_chance_buyer_id" in filter and filter["second_chance_buyer_id"]:
        second_chance_buyer_ids = filter["second_chance_buyer_id"] if isinstance(filter["second_chance_buyer_id"], list) else [filter["second_chance_buyer_id"]]
        filter["second_chance_buyer_id"] = {"$in": [ObjectId(agent_id) for agent_id in second_chance_buyer_ids]}
    if "lead_order_id" in filter:
        filter["lead_order_id"] = ObjectId(filter["lead_order_id"])
    if "second_chance_lead_order_id" in filter:
        filter["second_chance_lead_order_id"] = ObjectId(filter["second_chance_lead_order_id"])
    filter = _format_created_time_filter(filter)
    filter = _format_lead_sold_time_filter(filter)
    filter = _format_second_chance_lead_sold_time_filter(filter)
    return filter


def _handle_lead_received_date_filter(filter):
    if "lead_received_date_gte" in filter or "lead_received_date_lte" in filter:
        date_gte = filter.pop("lead_received_date_gte", None)
        date_lte = filter.pop("lead_received_date_lte", None)
        if date_gte:
            date_gte = datetime.strptime(date_gte, "%Y-%m-%dT%H:%M:%S.%fZ")
        if date_lte:
            date_lte = datetime.strptime(date_lte, "%Y-%m-%dT%H:%M:%S.%fZ")
        return filter, date_gte, date_lte
    return filter, None, None


def _build_aggregation_pipeline(filter, sort, page, limit, agent_id, date_gte, date_lte):
    match_conditions = []

    if filter:
        if "lead_type" in filter:
            if filter["lead_type"] == "Fresh":
                match_conditions.append({"buyer_id": ObjectId(agent_id)})
            elif filter["lead_type"] == "2nd Chance":
                match_conditions.append({"second_chance_buyer_id": ObjectId(agent_id)})
            filter.pop("lead_type")
        match_conditions.append(filter)

    lead_received_date_expr = {
        "$cond": [
            {"$eq": ["$buyer_id", agent_id]},
            "$lead_sold_time",
            {
                "$cond": [
                    {"$eq": ["$second_chance_buyer_id", agent_id]},
                    "$second_chance_lead_sold_time",
                    None
                ]
            }
        ]
    }

    date_expr_conditions = []
    if date_gte:
        date_expr_conditions.append({"$gte": [lead_received_date_expr, date_gte]})
    if date_lte:
        date_expr_conditions.append({"$lte": [lead_received_date_expr, date_lte]})

    if date_expr_conditions:
        if len(date_expr_conditions) == 1:
            date_condition = date_expr_conditions[0]
        else:
            date_condition = {"$and": date_expr_conditions}
        match_conditions.append({"$expr": date_condition})

    if match_conditions:
        if len(match_conditions) == 1:
            match_stage = {"$match": match_conditions[0]}
        else:
            match_stage = {"$match": {"$and": match_conditions}}
    else:
        match_stage = {"$match": {}}

    # Add filter after addFields for Fresh and 2nd Chance leads
    pipeline = [
        match_stage,
        {
            "$addFields": {
                "lead_received_date": lead_received_date_expr,
                "lead_type": {
                    "$cond": [
                        {"$eq": [agent_id, "$second_chance_buyer_id"]},
                        "2nd Chance",
                        "Fresh"
                    ]
                },
                "is_second_chance": {
                    "$eq": ["$lead_type", "2nd Chance"]
                }
            }
        },
        {
            "$project": {
                "first_name": 1,
                "last_name": 1,
                "email": 1,
                "phone": 1,
                "state": 1,
                "origin": 1,
                "lead_sold_time": 1,
                "second_chance_lead_sold_time": 1,
                "buyer_id": 1,
                "second_chance_buyer_id": 1,
                "lead_sold_by_agent_time": 1,
                "campaign_id": 1,
                "created_time": 1,
                "custom_fields": 1,
                "lead_received_date": 1,
                "lead_type": 1,
                "is_second_chance": 1
            }
        },
        {
            "$facet": {
                "data": [
                    {"$sort": {sort[0]: sort[1]}},
                    {"$skip": (page - 1) * limit},
                    {"$limit": limit}
                ],
                "total": [
                    {"$count": "count"}
                ]
            }
        }
    ]

    return pipeline


async def get_leads(ids: List[ObjectId], user: UserModel):
    lead_collection = get_lead_collection()
    if user.is_agent():
        lead_received_date_expr = {
            "$cond": [
                {"$eq": ["$buyer_id", user.agent_id]},
                "$lead_sold_time",
                {
                    "$cond": [
                        {"$eq": ["$second_chance_buyer_id", user.agent_id]},
                        "$second_chance_lead_sold_time",
                        None
                    ]
                }
            ]
        }
        match_conditions = {"_id": {"$in": [ObjectId(id) for id in ids]}}
        pipeline = [
            {"$match": match_conditions},
            {
                "$addFields": {
                    "lead_received_date": lead_received_date_expr,
                    "lead_type": {
                        "$cond": [
                            {"$eq": [user.agent_id, "$second_chance_buyer_id"]},
                            "2nd Chance",
                            "Fresh"
                        ]
                    },
                    "is_second_chance": {
                        "$eq": ["$lead_type", "2nd Chance"]
                    }
                }
            },
            {
                "$project": {
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "phone": 1,
                    "state": 1,
                    "origin": 1,
                    "lead_sold_time": 1,
                    "second_chance_lead_sold_time": 1,
                    "buyer_id": 1,
                    "second_chance_buyer_id": 1,
                    "lead_sold_by_agent_time": 1,
                    "campaign_id": 1,
                    "created_time": 1,
                    "custom_fields": 1,
                    "lead_received_date": 1,
                    "lead_type": 1,
                    "is_second_chance": 1
                }
            },
        ]
        leads_in_db = await lead_collection.aggregate(pipeline).to_list(None)
    else:
        leads_in_db = await lead_collection.find({"_id": {"$in": [ObjectId(id) for id in ids]}}).to_list(None)
    leads = [lead_model.LeadModel(**lead).to_json() for lead in leads_in_db]
    return leads


async def assign_lead_to_agent(lead: lead_model.LeadModel, lead_id: str):
    from app.controllers import agent as agent_controller
    from app.controllers import campaign as campaign_controller
    from app.controllers import order as order_controller
    from app.controllers import transaction as transaction_controller
    from app.controllers import user as user_controller
    lead_collection = get_lead_collection()
    campaign = await campaign_controller.get_one_campaign(lead.campaign_id)
    lead_price = campaign.price_per_lead
    agents_with_open_orders = await agent_controller.get_agents_with_open_orders(campaign_id=lead.campaign_id, lead=lead)
    if not agents_with_open_orders:
        logger.warning(f"No agents with balance found for lead {lead_id}")
        return
    logger.info(f"Agents with open orders: {agents_with_open_orders}")
    eligible_agents = await get_eligible_agents_for_lead(agents_with_open_orders, lead)
    if not eligible_agents:
        logger.warning(f"No agents licensed in {lead.state} with balance found for lead {lead_id}")
        return
    logger.info(f"Eligible agents: {eligible_agents}")
    agent_to_distribute: AgentModel = choose_agent(agents=eligible_agents, distribution_type="round_robin")
    if agent_to_distribute:
        if agent_to_distribute.lead_price_override:
            lead_price = agent_to_distribute.lead_price_override
        current_lead_order = await order_controller.get_oldest_open_order_by_agent_and_campaign(
            agent_id=agent_to_distribute.id,
            campaign_id=lead.campaign_id,
            is_second_chance=False
        )
        if current_lead_order:
            lead.lead_order_id = current_lead_order.id
        if agent_to_distribute.CRM.name:
            try:
                agent_crm = crm_chooser(agent_to_distribute.CRM.name)
            except ValueError as e:
                logger.error(f"Error choosing CRM for agent {agent_to_distribute.id}: {str(e)}")
                agent_crm = None
            if agent_crm and agent_to_distribute.CRM.integration_details:
                agent_integration_details = agent_to_distribute.CRM.integration_details[str(campaign.id)]
                fresh_creds = next(cred for cred in agent_integration_details if cred.type == 'fresh')
                if fresh_creds:
                    fresh_creds = fresh_creds.to_json()
                    fresh_creds.pop('type')
                    agent_crm = agent_crm(
                        integration_details=fresh_creds
                    )
                    agent_crm.push_lead(lead.crm_json())
                    logger.info(f"Lead {lead_id} pushed to CRM for agent {agent_to_distribute.id}")
        result = await lead_collection.update_one(
            {"_id": ObjectId(lead_id)},
            {"$set": {
                "buyer_id": agent_to_distribute.id,
                "lead_sold_time": datetime.utcnow(),
                "lead_order_id": lead.lead_order_id
            }}
        )
        if result.modified_count == 1:
            user = await user_controller.get_user_by_field(agent_id=agent_to_distribute.id)
            user_id = user.id
            if current_lead_order:
                await order_controller.check_order_amounts_and_close(current_lead_order)
            await transaction_controller.create_transaction(
                TransactionModel(
                    user_id=user_id,
                    amount=-lead_price,
                    description="Fresh Lead purchase",
                    type="debit",
                    date=datetime.utcnow(),
                    lead_id=ObjectId(lead_id),
                    campaign_id=lead.campaign_id
                )
            )
            logger.info(f"Lead {lead_id} assigned to agent {agent_to_distribute.id}")
    logger.info(f"Lead {lead_id} not assigned to any agent")


def choose_agent(agents, distribution_type):
    if distribution_type == "round_robin":
        return agents[0]
    elif distribution_type == "random":
        return random.choice(agents)


async def _is_second_chance_lead(lead_id: str):
    lead = await get_one_lead(lead_id)
    if lead.is_second_chance:
        return True
    return False


async def send_leads_to_agent(lead_ids: list, agent_id: str, campaign_id: str):
    from app.controllers import agent as agent_controller
    from app.controllers.campaign import get_one_campaign
    from app.controllers.user import get_user_by_field

    user = await get_user_by_field(agent_id=ObjectId(agent_id))
    campaign = await get_one_campaign(campaign_id)
    agent_id_obj = ObjectId(agent_id)
    agent = await agent_controller.get_agent_by_field(_id=agent_id_obj)

    if not agent:
        logger.warning(f"Agent {agent_id} not found")
        return
    second_chance_leads = [lead for lead in lead_ids if await _is_second_chance_lead(lead)]
    fresh_leads = [lead for lead in lead_ids if not await _is_second_chance_lead(lead)]
    try:
        if fresh_leads:
            await send_fresh_leads_to_agent(fresh_leads, agent, campaign, user=user)
        if second_chance_leads:
            await send_second_chance_leads_to_agent(second_chance_leads, agent, campaign, user=user)
        return True
    except Exception as e:
        logger.error(f"Error sending leads to agent {agent_id}: {str(e)}")
        return False


async def send_fresh_leads_to_agent(lead_ids: list, agent: dict, campaign: CampaignModel, user: UserModel):
    from app.controllers import order as order_controller
    from app.controllers import transaction as transaction_controller

    lead_collection = get_lead_collection()

    agent_id = agent["_id"]
    campaign_id = campaign.id

    oldest_open_order = await order_controller.get_oldest_open_order_by_agent_and_campaign(
            agent_id=str(agent_id),
            campaign_id=str(campaign_id),
            is_second_chance=False
        )
    result = await lead_collection.update_many(
        {"_id": {"$in": [ObjectId(id) for id in lead_ids]}},
        {"$set": {
            "buyer_id": agent_id,
            "lead_sold_time": datetime.utcnow(),
            "lead_order_id": oldest_open_order.id
        }}
    )
    if agent["CRM"]["name"]:
        agent_crm = crm_chooser(agent["CRM"]["name"])
        if agent_crm and agent["CRM"]["integration_details"]:
            agent_integration_details = agent["CRM"]["integration_details"][str(campaign_id)]
            fresh_creds = next(cred for cred in agent_integration_details if cred['type'] == 'fresh')
            fresh_creds.pop('type')
            agent_crm = agent_crm(
                integration_details=fresh_creds
            )
            for lead_id in lead_ids:
                lead = await get_one_lead(lead_id)
                agent_crm.push_lead(lead.crm_json())
                logger.info(f"Lead {lead_id} pushed to CRM for agent {agent_id}")
    else:
        logger.warning(f"No CRM found for agent {agent_id}")
    if agent["lead_price_override"]:
        lead_price = agent["lead_price_override"]
        logger.info(f"Lead price override found for agent {agent_id}")
    else:
        lead_price = campaign.price_per_lead
        logger.info(f"No lead price override found for agent {agent_id}")
    await transaction_controller.create_transaction(
        TransactionModel(
            user_id=user.id,
            amount=-lead_price * len(lead_ids),
            description="Leads sent by agency",
            type="debit",
            date=datetime.utcnow(),
            lead_id=[ObjectId(id) for id in lead_ids],
            campaign_id=campaign_id
        )
    )

    await order_controller.check_order_amounts_and_close(oldest_open_order)
    await order_controller.update_order(oldest_open_order.id, oldest_open_order)
    if result.modified_count == len(lead_ids):
        return True
    return False


async def send_second_chance_leads_to_agent(lead_ids: list, agent: AgentModel, campaign: CampaignModel, user: UserModel):
    from app.controllers import order as order_controller
    from app.controllers import transaction as transaction_controller

    lead_collection = get_lead_collection()

    agent_id = agent["_id"]
    campaign_id = campaign.id

    oldest_open_order = await order_controller.get_oldest_open_order_by_agent_and_campaign(
            agent_id=str(agent_id),
            campaign_id=str(campaign_id),
            is_second_chance=True
        )
    result = await lead_collection.update_many(
        {"_id": {"$in": [ObjectId(id) for id in lead_ids]}},
        {"$set": {
            "second_chance_buyer_id": agent_id,
            "second_chance_lead_sold_time": datetime.utcnow(),
            "second_chance_lead_order_id": oldest_open_order.id
        }}
    )
    if agent["CRM"]["name"]:
        agent_crm = crm_chooser(agent["CRM"]["name"])
        if agent_crm and agent["CRM"]["integration_details"]:
            agent_integration_details = agent["CRM"]["integration_details"][campaign_id]
            second_chance_creds = next(cred for cred in agent_integration_details if cred['type'] == 'second_chance')
            second_chance_creds.pop('type')
            agent_crm = agent_crm(
                integration_details=second_chance_creds
            )
            for lead_id in lead_ids:
                lead = await get_one_lead(lead_id)
                agent_crm.push_lead(lead.crm_json())
                logger.info(f"Lead {lead_id} pushed to CRM for agent {agent_id}")
    if agent["second_chance_lead_price_override"]:
        lead_price = agent["second_chance_lead_price_override"]
    else:
        lead_price = campaign.price_per_second_chance_lead
    await transaction_controller.create_transaction(
        TransactionModel(
            user_id=user.id,
            amount=-lead_price * len(lead_ids),
            description="Second Chance Leads sent by agency",
            type="debit",
            date=datetime.utcnow(),
            lead_id=[ObjectId(id) for id in lead_ids],
            campaign_id=campaign_id
        )
    )

    await order_controller.check_order_amounts_and_close(oldest_open_order)
    await order_controller.update_order(oldest_open_order.id, oldest_open_order)
    if result.modified_count == len(lead_ids):
        return True
    return False


async def get_eligible_agents_for_lead(agents: List[AgentModel], lead: lead_model.LeadModel):
    formatted_lead_state = formatter.format_state_to_abbreviation(lead.state)
    eligible_agents = []
    for agent in agents:
        if not lead.is_second_chance:
            daily_limit = await agent.campaign_daily_limit(lead.campaign_id)
            if not daily_limit:
                continue
            if await agent.todays_lead_count(lead.campaign_id) >= daily_limit:
                continue
        if formatted_lead_state in agent.states_with_license:
            if lead.is_second_chance:
                if lead.buyer_id == agent.id:
                    continue
                eligible_agents.append(agent)
            eligible_agents.append(agent)
    return eligible_agents


def _build_date_range_query(date_range: Dict[str, datetime],
                            date_field: str,
                            campaigns: List[bson.ObjectId],
                            is_second_chance: Optional[bool] = None) -> Dict:
    base_query = {
        date_field: {
            "$gte": date_range["start"],
            "$lte": date_range["end"]
        }
    }

    if campaigns:
        base_query["campaign_id"] = {"$in": campaigns}

    if is_second_chance is not None:
        if is_second_chance:
            base_query["$or"] = [
                {"is_second_chance": True},
                {"second_chance_buyer_id": {"$exists": True}}
            ]
        else:
            base_query["$and"] = [
                {"is_second_chance": False},
                {"buyer_id": {"$exists": True}}
            ]

    return base_query


async def get_lead_counts(date_ranges: Dict[str, Any], campaigns: List[bson.ObjectId]) -> Dict[str, Dict[str, int]]:
    if not date_ranges:
        return {}

    lead_collection = get_lead_collection()
    result = {
        "created": {},
        "fresh_sold": {},
        "second_chance_sold": {}
    }

    for period in ["thisWeek", "lastWeek", "thisMonth", "lastMonth"]:
        if period in date_ranges:
            created_query = _build_date_range_query(
                date_ranges[period],
                DateField.CREATED.value,
                campaigns
            )
            result["created"][period] = await lead_collection.count_documents(created_query)
            fresh_query = _build_date_range_query(
                date_ranges[period],
                DateField.SOLD.value,
                campaigns,
                False
            )
            result["fresh_sold"][period] = await lead_collection.count_documents(fresh_query)
            second_chance_query = _build_date_range_query(
                date_ranges[period],
                DateField.SECOND_CHANCE_SOLD.value,
                campaigns,
                True
            )
            result["second_chance_sold"][period] = await lead_collection.count_documents(second_chance_query)

    return result


async def get_unsold_leads(campaigns):
    lead_collection = get_lead_collection()
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    three_months_ago = now - timedelta(days=90)
    
    fresh_unsold_query = {
        "campaign_id": {"$in": campaigns},
        "created_time": {"$gte": seven_days_ago},
        "buyer_id": None,
        "is_second_chance": False,
        "$or": [
            {"custom_fields.invalid": {"$exists": False}},
            {"custom_fields.invalid": "no"}
        ]
    }

    second_chance_query = {
        "campaign_id": {"$in": campaigns},
        "created_time": {
            "$lte": thirty_days_ago,
            "$gte": three_months_ago
        },
        "second_chance_buyer_id": None,
        "is_second_chance": True,
        "$or": [
            {"custom_fields.invalid": {"$exists": False}},
            {"custom_fields.invalid": "no"}
        ]
    }

    invalid_query = {
        "campaign_id": {"$in": campaigns},
        "created_time": {"$gte": three_months_ago},
        "custom_fields.invalid": "yes"
    }

    fresh_unsold_in_db = await lead_collection.find(fresh_unsold_query).to_list(None)
    fresh_unsold = [lead_model.LeadModel(**lead).to_json() for lead in fresh_unsold_in_db]
    fresh_unsold_total = await lead_collection.count_documents(fresh_unsold_query)
    second_chance_unsold_in_db = await lead_collection.find(second_chance_query).to_list(None)
    second_chance_unsold = [lead_model.LeadModel(**lead).to_json() for lead in second_chance_unsold_in_db]

    second_chance_unsold_total = await lead_collection.count_documents(second_chance_query)

    return {
        "fresh_unsold": fresh_unsold,
        "fresh_unsold_total": fresh_unsold_total,
        "second_chance_unsold": second_chance_unsold,
        "second_chance_unsold_total": second_chance_unsold_total
    }


async def validate_lead(lead: lead_model.LeadModel) -> tuple:
    rejection_reasons = []
    if not lead.phone or not lead.email:
        rejection_reasons.append("Missing phone or email")
        return False, rejection_reasons
    format_number = formatter.format_phone_number(lead.phone)
    is_valid_phone = validator.validate_phone_number(format_number)
    if not is_valid_phone:
        rejection_reasons.append("Invalid phone number")
        return False, rejection_reasons
    is_duplicate = await validator.validate_duplicate(lead, lead.campaign_id)
    if is_duplicate:
        rejection_reasons.append("Duplicate lead")
        return False, rejection_reasons
    return True, rejection_reasons


async def assign_second_chance_lead_to_agent(lead: lead_model.LeadModel, lead_id: str):
    from app.controllers import agent as agent_controller
    from app.controllers import campaign as campaign_controller
    from app.controllers import order as order_controller
    from app.controllers import transaction as transaction_controller
    from app.controllers import user as user_controller
    lead_collection = get_lead_collection()
    campaign = await campaign_controller.get_one_campaign(lead.campaign_id)
    lead_price = campaign.price_per_second_chance_lead
    agents_with_open_orders = await agent_controller.get_agents_with_open_orders(campaign_id=lead.campaign_id, lead=lead)
    if not agents_with_open_orders:
        logger.warning(f"No agents with balance found for lead {lead_id}")
        return
    eligible_agents = await get_eligible_agents_for_lead(agents_with_open_orders, lead)
    if not eligible_agents:
        logger.warning(f"No agents licensed in {lead.state} with balance found for second chance lead {lead_id}")
        return
    agent_to_distribute: AgentModel = choose_agent(agents=eligible_agents, distribution_type="round_robin")
    if agent_to_distribute:
        if agent_to_distribute.second_chance_lead_price_override:
            lead_price = agent_to_distribute.second_chance_lead_price_override
        current_lead_order = await order_controller.get_oldest_open_order_by_agent_and_campaign(
            agent_id=agent_to_distribute.id,
            campaign_id=lead.campaign_id,
            is_second_chance=True
        )
        if current_lead_order:
            lead.second_chance_lead_order_id = current_lead_order.id
        if agent_to_distribute.CRM.name:
            agent_crm = crm_chooser(agent_to_distribute.CRM.name)
            if agent_crm and agent_to_distribute.CRM.integration_details:
                agent_integration_details = agent_to_distribute.CRM.integration_details[str(campaign.id)]
                second_chance_creds = next(cred for cred in agent_integration_details if cred['type'] == 'second_chance')
                if second_chance_creds:
                    second_chance_creds.pop('type')
                    agent_crm = agent_crm(
                        integration_details=second_chance_creds
                    )
                    agent_crm.push_lead(lead.crm_json())
                    logger.info(f"Second chance lead {lead_id} pushed to CRM for agent {agent_to_distribute.id}")
        result = await lead_collection.update_one(
            {"_id": ObjectId(lead_id)},
            {"$set": {
                "second_chance_buyer_id": agent_to_distribute.id,
                "second_chance_lead_sold_time": datetime.utcnow(),
                "second_chance_lead_order_id": lead.second_chance_lead_order_id
            }}
        )
        if result.modified_count == 1:
            user = await user_controller.get_user_by_field(agent_id=agent_to_distribute.id)
            user_id = user.id
            if current_lead_order:
                await order_controller.check_order_amounts_and_close(current_lead_order)
            await transaction_controller.create_transaction(
                TransactionModel(
                    user_id=user_id,
                    amount=-lead_price,
                    description="Second Chance Lead purchase",
                    type="debit",
                    date=datetime.utcnow(),
                    lead_id=ObjectId(lead_id),
                    campaign_id=lead.campaign_id
                )
            )


async def todays_lead_count_by_agent(agent_id: str, campaign_id: str) -> int:
    lead_collection = get_lead_collection()
    today = datetime.combine(datetime.utcnow(), datetime.min.time())
    tomorrow = today + timedelta(days=1)
    query = {
        "created_time": {"$gte": today, "$lt": tomorrow},
        "buyer_id": ObjectId(agent_id),
        "campaign_id": ObjectId(campaign_id)
    }
    return await lead_collection.count_documents(query)
