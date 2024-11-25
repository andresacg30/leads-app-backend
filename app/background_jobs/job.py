import logging
import typing
from rq.job import Job

from app.resources import rq


logger = logging.getLogger(__name__)


def get_scheduled_jobs():
    if rq is None:
        logger.warning("rq not initialized")
        return []
    jobs: typing.List[Job] = rq.get_jobs()
    logger.info(f"Getting scheduled jobs {jobs}")
    if len(jobs) == 1:
        return [jobs.to_dict()]
    return [job.to_dict() for job in jobs]


def clear_scheduled_jobs():
    if rq is None:
        logger.warning("rq not initialized")
        return
    jobs = rq.get_jobs()
    for job in jobs:
        job.delete()
    logger.info("Cleared all scheduled jobs")


def cancel_scheduled_jobs():
    if rq is None:
        logger.warning("rq not initialized")
        return
    jobs = rq.get_jobs()
    for job in jobs:
        job.cancel()
    logger.info("Canceled all scheduled jobs")


def schedule_job(job_name: str, job_args: dict, job_kwargs: dict, job_time: int):
    if rq is None:
        logger.warning("rq not initialized")
        return
    job = rq.enqueue_in(job_time, job_name, *job_args, **job_kwargs)
    logger.info(f"Scheduled job {job.id} for {job_time} seconds from now")
    return job.id


def enqueue_background_job(function_name, *args, **kwargs):
    if rq is None:
        logger.warning("rq not initialized")
        return
    job = rq.enqueue(function_name, *args, **kwargs)
    logger.info(f"Enqueued job {job.id}")
    return job.id


def cancel_job(job_id):
    if rq is None:
        logger.warning("rq not initialized")
        return
    job = rq.fetch_job(job_id)
    job.cancel()
    logger.info(f"Canceled job {job_id}")
    return job.id
