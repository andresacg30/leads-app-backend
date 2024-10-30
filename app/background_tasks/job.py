import logging
import typing
from rq.job import Job

from app.resources import scheduler


logger = logging.getLogger(__name__)


def get_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return []
    jobs: typing.List[Job] = scheduler.get_jobs()
    logger.info(f"Getting scheduled jobs {jobs}")
    return [job.to_dict() for job in jobs]


def clear_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return
    jobs = scheduler.get_jobs()
    for job in jobs:
        job.cancel()
    logger.info("Cleared all scheduled jobs")
