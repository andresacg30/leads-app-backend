import logging

from app.resources import scheduler


logger = logging.getLogger(__name__)


def get_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return []
    jobs = scheduler.get_jobs()
    logger.info(f"Getting scheduled jobs {jobs}")
    return list(jobs)
