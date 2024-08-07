import pytest
from faker import Faker


fake = Faker()


def test__create_agent_route__returns_201_created__when_adding_agent_for_first_time(agent_fixture, test_client):
    agent = agent_fixture

    response = test_client.post("/api/agent/", json=agent)

    assert response.status_code == 201


async def test__create_agent_route__returns_201_created__when_adding_agent_with_new_licensed_state(agent_fixture, test_client):
    agent = agent_fixture
    agent['states_with_license'].append(fake.state_abbr())

    response = test_client.post("/api/agent/", json=agent)

    assert response.status_code == 201


async def test__create_agent_route__returns_201_created__when_adding_agent_with_new_campaign(agent_factory, agent_fixture, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    agent['campaigns'] = [fake.state_abbr()]

    response = test_client.post("/api/agent/", json=agent)

    assert response.status_code == 201


async def test__create_agent_route__returns_409_exists__if_agent_exists_in_campaigns(agent_factory, agent_fixture, test_client):
    agent = agent_fixture
    await agent_factory(**agent)

    response = test_client.post("/api/agent/", json=agent)

    assert response.status_code == 409


@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone", "states_with_license", "CRM"])
async def test__create_agent_route__returns_422_unproessable_entity__if_required_field_is_missing(agent_fixture, test_client, field):
    agent = agent_fixture
    del agent[field]
    response = test_client.post("/api/agent/", json=agent)
    assert response.status_code == 422


async def test__list_agents_route__returns_200_ok__when_agents_exist_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['agents']) > 0


async def test__list_agents_route__returns_200_ok__when_agents_do_not_exist_in_database(test_client):
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['agents']) == 0


async def test__list_agents_route__returns_200_ok__when_more_than_one_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    second_agent = agent_fixture
    await agent_factory(**agent)
    await agent_factory(**second_agent)
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['agents']) > 1


async def test__show_agent_route__returns_200_ok__when_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.get(f"/api/agent/{inserted_agent.inserted_id}")
    assert response.status_code == 200


async def test__show_agent_route__returns_404_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.get(f"/api/agent/{invalid_object_id}")
    assert response.status_code == 404


async def test__update_agent_route__returns_200_ok__when_agent_exists_in_database_and_correct_fields_are_sent(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/agent/{inserted_agent.inserted_id}", json=updated_fields)
    assert response.status_code == 200


async def test__update_agent_route__returns_404_agent_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/agent/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 404
    assert response.json()['detail'] == f"Agent with id {invalid_object_id} not found"


async def test__update_agent_route__returns_400_agent_id_invalid__when_invalid_id_is_sent(test_client):
    invalid_object_id = fake.random_number(digits=12)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/agent/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 400
    assert response.json()['detail'] == f"Invalid id {invalid_object_id} on update agent route."


async def test__update_agent_route__returns_400_empty_agent__when_no_fields_are_sent(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.put(f"/api/agent/{inserted_agent.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__update_agent_route__returns_400_empty_agent__when_wrong_fields_are_sent(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.put(f"/api/agent/{inserted_agent.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__delete_agent_route__returns_204_no_content__when_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.delete(f"/api/agent/{inserted_agent.inserted_id}")
    assert response.status_code == 204


async def test__delete_agent_route__returns_404_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.delete(f"/api/agent/{invalid_object_id}")
    assert response.status_code == 404
