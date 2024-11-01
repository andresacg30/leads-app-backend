FROM python:3.9-slim
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV REDIS_URL=${REDIS_URL}
ENV REDIS_PORT=${REDIS_PORT}

CMD ["rq", "worker", "--url", "redis://${REDIS_URL}:${REDIS_PORT}/0", "default"]