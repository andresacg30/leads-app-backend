from faker import Faker


fake = Faker()


def test__create_agent_route__returns_201_created__when_adding_agent_for_first_time(agent_fixture, test_client):
    agent = agent_fixture
    response = test_client.post("/api/agent/", json=agent)
    assert response.status_code == 201


async def test__create_agent_route__returns_201_created__when_adding_agent_with_one_state_with_license(agent_factory, agent_fixture, test_client):
    agent = agent_fixture
    agent['states_with_license'] = [fake.state_abbr()]
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


async def test__create_agent_route__returns_422_unproessable_entity__if_email_is_missing(agent_fixture, test_client):
    agent = agent_fixture
    del agent['email']
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


async def test__list_agent_route__returns_200_ok__when_more_than_one_agent_exists_in_database(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    second_agent = agent_fixture
    await agent_factory(**agent)
    await agent_factory(**second_agent)
    response = test_client.get("/api/agent/")
    assert response.status_code == 200
    assert len(response.json()['agents']) > 1


# async def test__list_agent_route__returns_200_ok__when_agent_exists_in_database(agent_fixture, agent_factory, test_client):
#     agent = agent_fixture
#     inserted_id = await agent_factory(**agent).inserted_id
#     response = test_client.get(f"/api/agent/{inserted_id}")
#     assert response.status_code == 200


# async def test__list_agent_route__returns_404_not_found__when_agent_does_not_exist_in_database(agent_fixture, test_client):
#     agent = agent_fixture
#     response = test_client.get(f"/api/agent/{agent['email']}")
#     assert response.status_code == 404
