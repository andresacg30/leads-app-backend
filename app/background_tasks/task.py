import logging

from app.resources import scheduler


logger = logging.getLogger(__name__)


def get_scheduled_jobs():
    if scheduler is None:
        logger.warning("Scheduler not initialized")
        return []
    logger.info("Getting scheduled jobs")
    return list(scheduler.get_jobs())
