from datetime import timedelta

import app.controllers.user as user_controller

from app.tools.async_tools import run_async
from app.resources import scheduler


def add_to_otp_verification_queue(user_id: str):
    task_id = scheduler.enqueue_in(
        timedelta(seconds=15),
        run_async,
        user_controller.check_user_is_verified_and_delete,
        user_id
    )
    return task_id.result
