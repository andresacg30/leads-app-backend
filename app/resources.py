import logging

from collections import defaultdict
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler

from settings import get_settings

settings = get_settings()

logger = logging.getLogger(__name__)


user_connections = defaultdict(list)

try:
    redis = Redis(host=settings.redis_api_address, port=settings.redis_api_port)
    rq = Queue(name="main_queue", connection=redis)
    scheduler = Scheduler(name="main_queue", connection=redis)
    logger.info("Connected to Redis and RQ Scheduler")
except Exception as e:
    logger.error(f"Error connecting to Redis: {e}")
    redis = None
    rq = None
    scheduler = None
