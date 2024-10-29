from collections import defaultdict
from redis import Redis
from rq import Queue
from rq_scheduler import Scheduler

from settings import get_settings

settings = get_settings()


redis = Redis(host=settings.redis_api_address, port=settings.redis_api_port)

rq = Queue(connection=redis)

scheduler = Scheduler(connection=redis)

user_connections = defaultdict(list)
