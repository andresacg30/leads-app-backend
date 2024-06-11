FROM python:3.9

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app app
COPY main.py settings.py ./

EXPOSE 8080

CMD ["fastapi", "run", "main.py", "--port", "8080"]
