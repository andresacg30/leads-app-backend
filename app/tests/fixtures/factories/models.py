import pytest

from app.models.agent import AgentModel
from app.controllers.agent import get_agent_collection


@pytest.fixture
async def agent_factory():
    collection = get_agent_collection()

    async def create_agent(**kwargs):
        agent = AgentModel(**kwargs)
        inserted_agent = await collection.insert_one(agent.model_dump(by_alias=True, exclude={"id"}))
        return inserted_agent

    yield create_agent


@pytest.fixture(autouse=True)
async def clean_database():
    collection = get_agent_collection()
    await collection.delete_many({})