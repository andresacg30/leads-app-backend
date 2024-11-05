# Dockerfile

FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY settings.py .
COPY rq_dashboard_app.py .

EXPOSE 8080

CMD ["python", "rq_dashboard_app.py"]
