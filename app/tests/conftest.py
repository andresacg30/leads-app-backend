import pytest
from fastapi.testclient import TestClient
from main import app
from app.db import Database

from .fixtures import *  # noqa


class TestSettings:
    testing: bool = True
    mongodb_name: str = "test_db"


test_settings = TestSettings()


@pytest.fixture(scope="module")
def test_client():
    Database._instance = None
    Database(settings=test_settings)
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
    Database._instance.client.close()
