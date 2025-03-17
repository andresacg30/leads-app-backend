from datetime import datetime, timedelta
import logging

import bson

import app.controllers.lead as lead_controller

from app.background_jobs.job import enqueue_background_job
from app.models.lead import LeadModel
from app.tools.async_tools import run_async
from app.resources import rq


logger = logging.getLogger(__name__)


def process_lead(lead: LeadModel, lead_id: str):
    logger.info(f"Lead {lead_id} is being processed")
    task_id = rq.enqueue(
        run_async,
        lead_controller.assign_lead_to_agent,
        lead,
        lead_id
    )
    logger.info(f"Task ID for lead {lead.full_name}: {task_id}")
    return "Success"


async def process_second_chance_lead(lead_id: str):
    logger.info(f"Lead {lead_id} is being processed for second chance")
    lead = await lead_controller.get_one_lead(lead_id)
    if lead.lead_sold_by_agent_time:
        logger.info(f"Lead {lead_id} has already been sold by an agent")
        return "Lead already sold"
    lead.is_second_chance = True
    lead.became_second_chance_time = datetime.utcnow()
    await lead_controller.update_lead(lead_id, lead)
    task_id = rq.enqueue(
        run_async,
        lead_controller.assign_second_chance_lead_to_agent,
        lead,
        lead_id
    )
    logger.info(f"Task ID for lead {lead.full_name}: {task_id}")
    return "Success"


def send_leads_to_agent(lead_ids: list, agent_id: str, campaign_id: str):
    logger.info(f"Sending {len(lead_ids)} leads to agent {agent_id}")
    task_id = rq.enqueue(
        run_async,
        lead_controller.send_leads_to_agent,
        lead_ids,
        agent_id,
        campaign_id
    )
    logger.info(f"Task ID for agent {agent_id}: {task_id}")
    return "Success"


async def schedule_for_second_chance(lead: LeadModel, lead_id: str, time: int):
    # Bug: processing leads as second chance
    return
    logger.info(f"Scheduling lead {lead_id} for second chance")
    delay = timedelta(days=time)
    task_id = rq.enqueue_in(
        delay,
        run_async,
        process_second_chance_lead,
        lead_id
    )
    lead.second_chance_task_id = task_id.id
    await lead_controller.update_lead(lead_id, lead)
    logger.info(f"Task ID for lead {lead.full_name}: {task_id}")
    return "Success"


async def delete_background_task_by_lead_ids(lead_ids: list):
    logger.info(f"Deleting background tasks for {len(lead_ids)} leads")
    lead_collection = lead_controller.get_lead_collection()
    for lead_id in lead_ids:
        lead = await lead_controller.get_one_lead(lead_id)
        if lead.second_chance_task_id:
            try:
                enqueue_background_job(
                    'app.background_jobs.job.cancel_job',
                    lead.second_chance_task_id
                )
            except Exception as e:
                logger.error(f"Error deleting task {lead.second_chance_task_id}: {e}")
            lead.second_chance_task_id = None
            await lead_collection.update_one(
                {"_id": bson.ObjectId(lead_id)},
                {"$set": {"second_chance_task_id": None}}
            )
    return "Success"
