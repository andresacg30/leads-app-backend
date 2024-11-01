import os
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from fastapi import FastAPI
from starlette.middleware.wsgi import WSGIMiddleware
from rq_dashboard import default_settings
from rq_dashboard.cli import make_flask_app
import uvicorn


def create_rq_dashboard_app():
    redis_address = os.getenv('REDIS_API_ADDRESS', 'localhost')
    redis_port = os.getenv('REDIS_PORT', 6379)
    redis_url = f'redis://{redis_address}:{redis_port}'
    os.environ['REDIS_URL'] = redis_url

    app = make_flask_app(default_settings)
    return app


app = FastAPI()


flask_app = create_rq_dashboard_app()
app.mount("/dashboard", WSGIMiddleware(flask_app))


security = HTTPBasic()


@app.middleware("http")
async def basic_auth(request: Request, call_next):
    if request.url.path.startswith("/dashboard"):
        credentials: HTTPBasicCredentials = await security(request)
        correct_username = secrets.compare_digest(credentials.username, os.getenv('DASHBOARD_USERNAME', 'admin'))
        correct_password = secrets.compare_digest(credentials.password, os.getenv('DASHBOARD_PASSWORD', 'password'))
        if not (correct_username and correct_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    response = await call_next(request)
    return response


@app.get("/health")
def health_check():
    return {"status": "OK"}


if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
