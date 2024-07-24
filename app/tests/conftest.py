import pytest
from fastapi.testclient import TestClient
from main import app
from settings import get_settings, Settings
from app.db import Database


class TestSettings(Settings):
    environment: str = "test"
    mongodb_url: str = "mongodb://localhost:27017"


test_settings = TestSettings()


def override_get_settings():
    return test_settings


@pytest.fixture(scope="module")
def test_client():
    app.dependency_overrides[get_settings] = override_get_settings
    Database.initialize(test_settings)
    client = TestClient(app)
    yield client
    app.dependency_overrides = {}
