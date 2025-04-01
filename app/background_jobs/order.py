from datetime import datetime, timedelta
import logging
from typing import List

import bson

from app.tools.async_tools import run_async
from app.resources import rq
from app.models.user import UserModel


logger = logging.getLogger(__name__)


async def schedule_order_priority_end(order_ids: List[bson.ObjectId], time: timedelta):
    from app.controllers.order import cancel_orders_prioritization, get_order_collection
    logger.info(f"Starting prioritization for orders {order_ids} at {time} seconds")
    task_id = rq.enqueue_in(
        time,
        run_async,
        cancel_orders_prioritization,
        order_ids
    )
    for order_id in order_ids:
        order = await get_order_collection().update_one(
            {"_id": order_id},
            {"$set": {"priority.task_id": task_id.id}}
        )
    logger.info(f"Scheduled prioritization for orders {order_ids} with task ID {task_id.id}")
    return "Success"
