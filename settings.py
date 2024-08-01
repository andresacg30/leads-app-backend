import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Settings(BaseSettings):
    mongodb_url: str = os.environ.get("MONGO_URL")
    environment: str = os.environ.get("ENVIRONMENT", "development")
    mongodb_name: str = os.environ.get("MONGO_DB_NAME")
    testing: bool = False


def get_settings() -> Settings:
    return Settings()
