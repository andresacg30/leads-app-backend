import motor.motor_asyncio
from settings import get_settings
import motor
import mongomock_motor


class Database:
    _instance = None

    def __new__(cls, settings=None):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            if settings is None:
                settings = get_settings()
            if settings.testing:
                cls._instance.client = mongomock_motor.AsyncMongoMockClient()
                cls._instance.db = cls._instance.client[settings.mongodb_name]
            else:
                cls._instance.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_url)
                cls._instance.db = cls._instance.client[settings.mongodb_name]
        return cls._instance

    @classmethod
    def get_db(cls):
        if cls._instance is None:
            cls()
        return cls._instance.db
