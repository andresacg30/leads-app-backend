import pytest
from faker import Faker


fake = Faker()


def test__create_lead_route__returns_201_created__when_passing_correct_lead_fields(lead_fixture, test_client):
    lead = lead_fixture

    response = test_client.post("/api/lead/", json=lead)

    assert response.status_code == 201


async def test__create_lead_route__returns_400_exists__if_agent_wrong_state_format_is_passed(lead_factory, lead_fixture, test_client):
    lead = lead_fixture
    lead['state'] = "wrong_state"
    await lead_factory(**lead)

    response = test_client.post("/api/lead/", json=lead)

    assert response.status_code == 400


@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone", "states_with_license", "CRM"])
async def test__create_agent_route__returns_422_unproessable_entity__if_required_field_is_missing(lead_fixture, test_client, field):
    lead = lead_fixture
    del lead[field]
    response = test_client.post("/api/lead/", json=lead)
    assert response.status_code == 422


async def test__list_agents_route__returns_200_ok__when_agents_exist_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    await lead_factory(**lead)
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) > 0


async def test__list_agents_route__returns_200_ok__when_agents_do_not_exist_in_database(test_client):
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) == 0


async def test__list_agents_route__returns_200_ok__when_more_than_one_agent_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    second_agent = lead_fixture
    await lead_factory(**lead)
    await lead_factory(**second_agent)
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) > 1


async def test__show_agent_route__returns_200_ok__when_agent_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/{inserted_agent.inserted_id}")
    assert response.status_code == 200


async def test__show_agent_route__returns_404_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.get(f"/api/lead/{invalid_object_id}")
    assert response.status_code == 404


async def test__update_agent_route__returns_200_ok__when_agent_exists_in_database_and_correct_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/lead/{inserted_agent.inserted_id}", json=updated_fields)
    assert response.status_code == 200


async def test__update_agent_route__returns_404_agent_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/lead/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 404
    assert response.json()['detail'] == f"Agent with id {invalid_object_id} not found"


async def test__update_agent_route__returns_400_agent_id_invalid__when_invalid_id_is_sent(test_client):
    invalid_object_id = fake.random_number(digits=12)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/lead/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 400
    assert response.json()['detail'] == f"Invalid id {invalid_object_id} on update lead route."


async def test__update_agent_route__returns_400_empty_agent__when_no_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/{inserted_agent.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__update_agent_route__returns_400_empty_agent__when_wrong_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/{inserted_agent.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__delete_agent_route__returns_204_no_content__when_agent_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    response = test_client.delete(f"/api/lead/{inserted_agent.inserted_id}")
    assert response.status_code == 204


async def test__delete_agent_route__returns_404_not_found__when_agent_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.delete(f"/api/lead/{invalid_object_id}")
    assert response.status_code == 404


@pytest.mark.parametrize("field", ["email", "phone"])
async def test__get_agent_id_by_field_route__returns_200_ok__when_agent_field_exists_in_database(lead_fixture, lead_factory, test_client, field):
    lead = lead_fixture
    inserted_agent = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/find/?{field}={lead[field]}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_agent.inserted_id)


async def test__get_agent_id_by_field_route__returns_200_ok__when_agent_full_name_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    agent_full_name = f"{lead['first_name']} {lead['last_name']}"
    inserted_agent = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/find/?full_name={agent_full_name}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_agent.inserted_id)


async def test__get_agent_id_by_field_route__returns_404_not_found__when_agent_field_does_not_exist_in_database(test_client):
    response = test_client.get(f"/api/lead/find/?email={fake.email()}")
    assert response.status_code == 404


@pytest.mark.parametrize("field", ["first_name", "last_name"])
async def test__get_agent_id_by_field_route__returns_400__when_sending_only_first_or_last_name_by_itself(test_client, field):
    response = test_client.get(f"/api/lead/find/?{field}={fake.name()}")
    assert response.status_code == 400
    assert response.json()['detail'] == "First name and last name must be provided together"
