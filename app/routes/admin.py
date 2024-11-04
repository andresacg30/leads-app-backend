import rq_dashboard
import fastapi
from flask import Flask
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import RedirectResponse


router = fastapi.APIRouter(prefix="/admin", tags=["admin"])


def create_rq_dashboard_app():
    app = Flask(__name__)
    app.config.from_object(rq_dashboard.default_settings)
    app.register_blueprint(rq_dashboard.blueprint, url_prefix="/dashboard")
    return app


app = fastapi.FastAPI()
flask_app = create_rq_dashboard_app()
app.mount("/dashboard", WSGIMiddleware(flask_app))


@app.get("/admin/dashboard")
def admin_dashboard():
    return RedirectResponse(url="/dashboard")
