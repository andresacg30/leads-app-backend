import logging
import rq_dashboard
import os
from flask import Flask
from settings import get_redis_settings
from fastapi import APIRouter, FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware


app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_redis_settings()
router = APIRouter(prefix="/admin", tags=["admin"])


class RedisSettings(object):
    def __init__(self):
        self.redis_api_address = settings.redis_api_address
        self.redis_api_port = settings.redis_api_port
        self.RQ_DASHBOARD_REDIS_URL = [f'redis://{self.redis_api_address}:{self.redis_api_port}']
        self.REDIS_URL = f'redis://{self.redis_api_address}:{self.redis_api_port}'


class RootPathMiddleware:
    def __init__(self, app, root_path):
        self.app = app
        self.root_path = root_path

    def __call__(self, environ, start_response):
        environ['SCRIPT_NAME'] = self.root_path
        path_info = environ.get('PATH_INFO', '')
        if path_info.startswith(self.root_path):
            environ['PATH_INFO'] = path_info[len(self.root_path):]
        return self.app(environ, start_response)


def create_rq_dashboard_app():
    rq_dashboard_path = os.path.dirname(rq_dashboard.__file__)

    app = Flask(
        __name__,
        static_folder=os.path.join(rq_dashboard_path, 'static'),
        static_url_path='/admin/dashboard/static'
    )

    app.config.from_object(RedisSettings())
    app.register_blueprint(rq_dashboard.blueprint, url_prefix='')
    return app


flask_app = RootPathMiddleware(create_rq_dashboard_app(), '/admin/dashboard')


app.mount('/admin/dashboard', WSGIMiddleware(flask_app))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
