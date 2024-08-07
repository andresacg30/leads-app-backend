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

    return create_agent
