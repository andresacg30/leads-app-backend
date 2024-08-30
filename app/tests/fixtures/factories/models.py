import pytest
from faker import Faker

from app.models.agent import AgentModel
from app.models.lead import LeadModel
from app.models.campaign import CampaignModel
from app.controllers.agent import get_agent_collection
from app.controllers.lead import get_lead_collection
from app.controllers.campaign import get_campaign_collection


fake = Faker()


@pytest.fixture
async def agent_factory():
    collection = get_agent_collection()

    async def create_agent(use_fixture_model=False, **kwargs):
        if use_fixture_model:
            agent = AgentModel(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.msisdn(),
                states_with_license=[fake.state() for _ in range(3)],
                CRM={
                    "name": "Ringy",
                    "integration_details": {
                        "auth_token": fake.password(),
                        "sid": fake.password()
                    }
                },
                credentials={
                    "username": fake.user_name(),
                    "password": fake.password()
                },
                campaigns=[fake.uuid4() for _ in range(3)]
            )
            agent.created_time = kwargs.get("created_time", agent.created_time.isoformat())
        else:
            agent = AgentModel(**kwargs)

        inserted_agent = await collection.insert_one(agent.model_dump(by_alias=True, exclude={"id"}))
        return inserted_agent

    yield create_agent


@pytest.fixture
async def lead_factory():
    collection = get_lead_collection()

    async def create_lead(use_fixture_model=False, **kwargs):
        if use_fixture_model:
            lead = LeadModel(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.msisdn(),
                state=fake.state(),
                origin="facebook",
                campaign_id=fake.uuid4(),
                custom_fields={}
            )
            lead.created_time = kwargs.get("created_time", lead.created_time.isoformat())
        else:
            lead = LeadModel(**kwargs)
        inserted_lead = await collection.insert_one(lead.model_dump(by_alias=True, exclude={"id"}))
        return inserted_lead

    yield create_lead


@pytest.fixture
async def campaign_factory():
    collection = get_campaign_collection()

    async def create_campaign(use_fixture_model=False, **kwargs):
        if use_fixture_model:
            campaign = CampaignModel(
                name=fake.company(),
                active=fake.boolean(),
                start_date=fake.date_time_this_decade()
            )
        else:
            campaign = CampaignModel(**kwargs)
        inserted_campaign = await collection.insert_one(campaign.model_dump(by_alias=True, exclude={"id"}))
        return inserted_campaign

    yield create_campaign


@pytest.fixture(autouse=True)
async def clean_database():
    collections = [get_agent_collection(), get_lead_collection(), get_campaign_collection()]
    for collection in collections:
        await collection.delete_many({})
