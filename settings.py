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
    api_key: str = os.environ.get("API_KEY")
    testing: bool = False
    stripe_api_key: str = os.environ.get("STRIPE_API_KEY")
    frontend_url: str = os.environ.get("FRONTEND_URL")
    mailgun_api_key: str = os.environ.get("MAILGUN_API_KEY")
    redis_api_address: str = os.environ.get("REDIS_API_ADDRESS")
    redis_api_port: int = os.environ.get("REDIS_API_PORT")
    stripe_payment_endpoint_secret: str = os.environ.get("STRIPE_PAYMENT_ENDPOINT_SECRET") or None


class RedisSettings(BaseSettings):
    redis_api_address: str = os.environ.get("REDIS_API_ADDRESS")
    redis_api_port: int = os.environ.get("REDIS_API_PORT")


def get_settings() -> Settings:
    return Settings()


def get_redis_settings() -> RedisSettings:
    return RedisSettings()
