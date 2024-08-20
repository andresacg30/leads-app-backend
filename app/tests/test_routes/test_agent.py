import datetime
import json
import pytest
import freezegun
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


@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone", "states_with_license"])
async def test__create_agent_route__returns_422_unproessable_entity__if_required_field_is_missing(agent_fixture, test_client, field):
    agent = agent_fixture
    del agent[field]
    response = test_client.post("/api/agent/", json=agent)
    assert response.status_code == 422


async def test__list_agents_route__returns_200_ok__when_agents_exist_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    response = test_client.get("/api/agent/?sort=id=ASC")
    assert response.status_code == 200
    assert len(response.json()['data']) > 0
    assert response.json()['total'] > 0


async def test__list_agents_route__returns_200_ok__when_agents_do_not_exist_in_database(test_client):
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['data']) == 0


async def test__list_agents_route__returns_200_ok__when_more_than_one_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    second_agent = agent_fixture
    await agent_factory(**agent)
    await agent_factory(**second_agent)
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['data']) > 1


async def test__list_agents_route_returns_200_ok_and_sorted_by_id__when_sort_query_is_valid(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    await agent_factory(**agent)
    response = test_client.get("/api/agent/?sort=id=ASC")
    assert response.status_code == 200
    assert response.json()['data'][0]['id'] < response.json()['data'][1]['id']


@freezegun.freeze_time('2021-01-01')
async def test__list_agents_route_returns_200_ok_and_correctly_sorted__when_sort_query_is_created_time(agent_fixture, agent_factory, test_client):
    now_time = datetime.datetime.now()
    agent = agent_fixture
    agent["created_time"] = now_time
    await agent_factory(**agent)
    await agent_factory(use_fixture_model=True, created_time=now_time + datetime.timedelta(days=1))
    response = test_client.get("/api/agent/?sort=created_time=ASC")
    assert response.status_code == 200
    assert response.json()['data'][0]['created_time'] < response.json()['data'][1]['created_time']


async def test__list_agents_route__returns_only_1_agent__when_limit_query_is_1(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    await agent_factory(use_fixture_model=True)
    response = test_client.get("/api/agent/?limit=1")
    assert response.status_code == 200
    assert len(response.json()['data']) == 1


async def test__list_agents_route__returns_last_agent__when_page_query_is_2(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    second_inserted_agent = await agent_factory(use_fixture_model=True)
    response = test_client.get("/api/agent/?page=2&limit=1")
    assert response.status_code == 200
    assert len(response.json()['data']) == 1
    assert response.json()['data'][0]['id'] == str(second_inserted_agent.inserted_id)
    assert response.json()['data'][0]['id'] != str(inserted_agent.inserted_id)


async def test_list_agent_rout__returns_correct_agent__when_filter_is_email(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    second_inserted_agent = await agent_factory(use_fixture_model=True)
    response = test_client.get("/api/agent/?filter={\"email\":\"%s\"}" % agent['email'])
    assert response.status_code == 200
    assert response.json()['data'][0]['email'] == agent['email']
    assert response.json()['data'][0]['id'] == str(inserted_agent.inserted_id)
    assert len(response.json()['data']) == 1
    assert second_inserted_agent.inserted_id not in [agent['id'] for agent in response.json()['data']]


@pytest.mark.skip(reason="Need to change the way the filter is being passed when filtering by dates")
@freezegun.freeze_time('2021-01-01')
async def test__list_agents_route__returns_agents__when_filter_is_created_time(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    agent['created_time'] = datetime.datetime.now()
    inserted_agent = await agent_factory(**agent)
    second_inserted_agent = await agent_factory(use_fixture_model=True, created_time=datetime.datetime.now() - datetime.timedelta(days=1))
    response = test_client.get("/api/agent/?filter={\"created_time\":\"%s\"}" % agent['created_time'])
    assert response.status_code == 200
    assert response.json()['data'][0]['id'] == str(inserted_agent.inserted_id)
    assert len(response.json()['data']) == 1
    assert second_inserted_agent.inserted_id not in [agent['id'] for agent in response.json()['data']]


async def test__list_agents_route__returns_400_bad_request__when_sort_query_is_invalid(test_client):
    response = test_client.get("/api/agent/?sort=id=INVALID")
    assert response.status_code == 400


async def test__show_agent_route__returns_200_ok__when_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.get(f"/api/agent/{inserted_agent.inserted_id}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_agent.inserted_id)


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
    assert response.json()['id'] == str(inserted_agent.inserted_id)


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


@pytest.mark.parametrize("field", ["email", "phone", "full_name"])
async def test__get_agent_id_by_field_route__returns_200_ok__when_agent_field_exists_in_database(agent_fixture, agent_factory, test_client, field):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    response = test_client.get(f"/api/agent/find/?{field}={agent[field]}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_agent.inserted_id)


async def test__get_agent_id_by_field_route__returns_404_not_found__when_agent_field_does_not_exist_in_database(test_client):
    response = test_client.get(f"/api/agent/find/?email={fake.email()}")
    assert response.status_code == 404


@pytest.mark.parametrize("field", ["first_name", "last_name"])
async def test__get_agent_id_by_field_route__returns_400__when_sending_only_first_or_last_name_by_itself(test_client, field):
    response = test_client.get(f"/api/agent/find/?{field}={fake.name()}")
    assert response.status_code == 400
    assert response.json()['detail'] == "First name and last name must be provided together"


async def test__get_multiple_agents_route__returns_200_ok__when_only_one_agent_exist_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    payload = json.dumps([str(inserted_agent.inserted_id)])
    response = test_client.post("/api/agent/get-many", data=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert len(response.json()['data']) == 1


async def test__get_multiple_agents_route__returns_200_ok__when_multiple_agents_exist_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    second_inserted_agent = await agent_factory(use_fixture_model=True)
    payload = json.dumps([str(inserted_agent.inserted_id), str(second_inserted_agent.inserted_id)])
    response = test_client.post("/api/agent/get-many", data=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert len(response.json()['data']) == 2
    assert response.json()['data'][0]['id'] == str(inserted_agent.inserted_id)
    assert response.json()['data'][1]['id'] == str(second_inserted_agent.inserted_id)


async def test__get_multiple_agents_route__returns_404_not_found__when_no_agents_exist_in_database(test_client):
    payload = json.dumps([fake.hexify(text='^' * 24)])
    response = test_client.post("/api/agent/get-many", data=payload, headers={"Content-Type": "application/json"})
    assert response.status_code == 404
