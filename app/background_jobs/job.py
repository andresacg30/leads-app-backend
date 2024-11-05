import logging
import typing
from rq.job import Job

from app.resources import rq as scheduler


logger = logging.getLogger(__name__)


def get_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return []
    jobs: typing.List[Job] = scheduler.get_jobs()
    logger.info(f"Getting scheduled jobs {jobs}")
    if len(jobs) == 1:
        return [jobs.to_dict()]
    return [job.to_dict() for job in jobs]


def clear_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return
    jobs = scheduler.get_jobs()
    for job in jobs:
        job.delete()
    logger.info("Cleared all scheduled jobs")


def cancel_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return
    jobs = scheduler.get_jobs()
    for job in jobs:
        job.cancel()
    logger.info("Canceled all scheduled jobs")
