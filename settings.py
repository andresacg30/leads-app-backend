import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Settings(BaseSettings):
    mongodb_url: str = os.environ.get("MONGO_URL")
    environment: str = os.environ.get("ENVIRONMENT", "development")
    mongodb_name: str = os.environ.get("MONGO_DB_NAME")
    realm_app_id: str = os.environ.get("REALM_APP_ID")
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY")
    email_address: str = os.environ.get("EMAIL_ADDRESS")
    email_password: str = os.environ.get("EMAIL_PASSWORD")
    email_service: str = os.environ.get("EMAIL_SERVICE")
    email_port: int = os.environ.get("EMAIL_PORT")
    api_key: str = os.environ.get("API_KEY")
    testing: bool = False
    stripe_api_key: str = os.environ.get("STRIPE_API_KEY")
    frontend_url: str = os.environ.get("FRONTEND_URL")


def get_settings() -> Settings:
    return Settings()
