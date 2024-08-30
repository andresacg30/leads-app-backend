import pytest
from faker import Faker

from app.models.agent import AgentModel
from app.models.lead import LeadModel
from app.models.campaign import CampaignModel

fake = Faker()


@pytest.fixture
def agent_fixture():
    agent = AgentModel(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        phone=fake.msisdn(),
        states_with_license=[fake.state() for _ in range(3)],
        CRM={
            "name": "Ringy",
            "url": "www.ringy.com",
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
    agent.created_time = agent.created_time.isoformat()
    return agent.model_dump()


@pytest.fixture
def lead_fixture():
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
    lead.created_time = lead.created_time.isoformat()
    return lead.model_dump()


@pytest.fixture
def campaign_fixture():
    campaign = CampaignModel(
        name=fake.company(),
        active=fake.boolean(),
        start_date=fake.date_time_this_decade()
    )
    campaign.start_date = campaign.start_date.isoformat()
    return campaign.model_dump()
