import logging
import os
import threading
from fastapi import FastAPI
import uvicorn
import redis
from rq import Worker


logger = logging.getLogger(__name__)
app = FastAPI()


@app.get("/")
def health_check():
    return {"status": "OK"}


def start_api():
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)


if __name__ == "__main__":
    api_thread = threading.Thread(target=start_api)
    api_thread.start()

    redis_server = os.getenv('REDIS_API_ADDRESS', 'localhost')
    redis_port = os.getenv('REDIS_PORT', 6379)
    redis_password = os.getenv('REDIS_PASSWORD', None)
    redis_url = f'redis://{redis_server}:{redis_port}'
    try:
        conn = redis.Redis(
            host=redis_server,
            port=redis_port
        )
        conn.ping()
        logger.info(f"Connected to Redis at {redis_url}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {redis_url}")
        raise e
    worker = Worker(['default'], connection=conn)
    worker.work()
