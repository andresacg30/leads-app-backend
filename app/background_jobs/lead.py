import logging

import app.controllers.lead as lead_controller

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
    return task_id.result
