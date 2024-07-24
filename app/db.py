import motor.motor_asyncio
from mongomock_motor import AsyncMongoMockClient


class Database:
    client = None
    db = None

    @classmethod
    def initialize(cls, settings=None):
        if settings is None:
            from settings import get_settings
            settings = get_settings()

        cls.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url) if settings.environment != "test" else AsyncMongoMockClient()
        cls.db = cls.client.leadconex

    @classmethod
    def get_db(cls, settings=None):
        if cls.db is None:
            cls.initialize(settings)
        return cls.db


db = Database.get_db()
