import pytest
from faker import Faker

from app.models.agent import AgentModel
from app.models.lead import LeadModel

fake = Faker()


@pytest.fixture
def agent_fixture():
    agent = AgentModel(
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        phone=fake.phone_number(),
        states_with_license=[fake.state_abbr() for _ in range(3)],
        CRM={
            "name": "Ringy",
            "url": fake.url(),
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
        phone=fake.phone_number(),
        state=fake.state_abbr(),
        origin="facebook",
        campaign_id=fake.uuid4(),
        custom_fields={}
    )
    lead.created_time = lead.created_time.isoformat()
    return lead.model_dump()



