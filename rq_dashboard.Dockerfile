# Base image
FROM python:3.9-slim

# Install rq-dashboard
RUN pip install --no-cache-dir rq-dashboard

# Expose the port (default is 9181)
EXPOSE 9181

ENV REDIS_URL=${REDIS_URL}
ENV REDIS_PORT=${REDIS_PORT}

# Command to run rq-dashboard
CMD ["rq-dashboard", "--redis-url", "redis://${REDIS_URL}:${REDIS_PORT}/0", "--port", "9181", "--bind", "0.0.0.0"]