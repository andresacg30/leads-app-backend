import logging
from datetime import timedelta

import app.controllers.user as user_controller

from app.tools.async_tools import run_async
from app.resources import rq


logger = logging.getLogger(__name__)


def add_to_otp_verification_queue(user_id: str):
    logger.info(f"Adding user {user_id} to OTP verification queue")
    task_id = rq.enqueue_in(
        timedelta(seconds=15),
        run_async,
        user_controller.check_user_is_verified_and_delete,
        user_id
    )
    logger.info(f"Task ID for user {user_id}: {task_id}")
    return task_id.result
