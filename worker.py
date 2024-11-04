# worker.py

import os
import threading
from fastapi import FastAPI
import uvicorn
import redis
from rq import Worker


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
    conn = redis.from_url(redis_url, password=redis_password)
    worker = Worker(['default'], connection=conn)
    worker.work()
