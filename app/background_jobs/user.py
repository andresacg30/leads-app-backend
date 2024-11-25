import logging
from datetime import timedelta

import app.controllers.user as user_controller

from app.models.user import UserModel
from app.tools.async_tools import run_async
from app.resources import rq


logger = logging.getLogger(__name__)


async def add_to_otp_verification_queue(user: UserModel):
    logger.info(f"Adding user {user.id} to OTP verification queue")
    task = rq.enqueue_in(
        timedelta(minutes=15),
        run_async,
        user_controller.check_user_is_verified_and_delete,
        user.id
    )
    user.account_creation_task_id = task.id
    await user_controller.update_user(user=user)
    logger.info(f"Task ID for user {user.id}: {task.id}")
    return task.result
