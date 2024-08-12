import pytest

from app.models.agent import AgentModel
from app.controllers.agent import get_agent_collection
from app.controllers.lead import get_lead_collection


@pytest.fixture
async def agent_factory():
    collection = get_agent_collection()

    async def create_agent(**kwargs):
        agent = AgentModel(**kwargs)
        inserted_agent = await collection.insert_one(agent.model_dump(by_alias=True, exclude={"id"}))
        return inserted_agent

    yield create_agent


@pytest.fixture
async def lead_factory():
    collection = get_lead_collection()

    async def create_lead(**kwargs):
        lead = AgentModel(**kwargs)
        inserted_lead = await collection.insert_one(lead.model_dump(by_alias=True, exclude={"id"}))
        return inserted_lead

    yield create_lead


@pytest.fixture(autouse=True)
async def clean_database():
    collection = get_agent_collection()
    await collection.delete_many({})