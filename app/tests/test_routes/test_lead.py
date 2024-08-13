import pytest
from faker import Faker


fake = Faker()


def test__create_lead_route__returns_201_created__when_passing_correct_lead_fields(lead_fixture, test_client):
    lead = lead_fixture

    response = test_client.post("/api/lead/", json=lead)

    assert response.status_code == 201


async def test__create_lead_route__returns_400_exists__if_lead_invalid_state_is_passed(lead_fixture, test_client):
    lead = lead_fixture
    lead['state'] = "wrong_state"

    response = test_client.post("/api/lead/", json=lead)

    assert response.status_code == 400


@pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone", "state", "campaign_id"])
async def test__create_lead_route__returns_422_unproessable_entity__if_required_field_is_missing(lead_fixture, test_client, field):
    lead = lead_fixture
    del lead[field]
    response = test_client.post("/api/lead/", json=lead)
    assert response.status_code == 422


async def test__list_leads_route__returns_200_ok__when_leads_exist_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    await lead_factory(**lead)
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) > 0


async def test__list_leads_route__returns_200_ok__when_leads_do_not_exist_in_database(test_client):
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) == 0


async def test__list_leads_route__returns_200_ok__when_more_than_one_lead_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    second_lead = lead_fixture
    await lead_factory(**lead)
    await lead_factory(**second_lead)
    response = test_client.get("/api/lead/")
    assert response.status_code == 200
    assert len(response.json()['leads']) > 1


async def test__show_lead_route__returns_200_ok__when_lead_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/{inserted_lead.inserted_id}")
    assert response.status_code == 200


async def test__show_lead_route__returns_404_not_found__when_lead_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.get(f"/api/lead/{invalid_object_id}")
    assert response.status_code == 404


async def test__update_lead_route__returns_200_ok__when_lead_exists_in_database_and_normal_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name()}
    response = test_client.put(f"/api/lead/{inserted_lead.inserted_id}", json=updated_fields)
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_lead.inserted_id)


async def test__update_lead_route__returns_404_lead_not_found__when_lead_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/lead/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 404
    assert response.json()['detail'] == f"Lead with id {invalid_object_id} not found"


async def test__update_lead_route__returns_400_lead_id_invalid__when_invalid_id_is_sent(test_client):
    invalid_object_id = fake.random_number(digits=12)
    updated_fields = {"email": fake.email(), "first_name": fake.first_name(), "campaigns": [fake.random_number(digits=2)]}
    response = test_client.put(f"/api/lead/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 400
    assert response.json()['detail'] == f"Invalid id {invalid_object_id} on update lead route"


async def test__update_lead_route__returns_400_empty_lead__when_no_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/{inserted_lead.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__update_lead_route__returns_400_empty_lead__when_wrong_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/{inserted_lead.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400


async def test__delete_lead_route__returns_204_no_content__when_lead_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.delete(f"/api/lead/{inserted_lead.inserted_id}")
    assert response.status_code == 204


async def test__delete_lead_route__returns_404_not_found__when_lead_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    response = test_client.delete(f"/api/lead/{invalid_object_id}")
    assert response.status_code == 404


async def test__get_lead_id_by_field_route__returns_200_ok__when_lead_email_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/find/?email={lead['email']}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_lead.inserted_id)


async def test__get_lead_id_by_field_route__returns_200_ok__when_agent_name_is_sent(lead_fixture, agent_fixture, lead_factory, agent_factory, test_client):
    lead = lead_fixture
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    lead["buyer_id"] = str(inserted_agent.inserted_id)
    lead["lead_sold_time"] = fake.date_time()
    inserted_lead = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/find/?email={lead['email']}&buyer_name={agent['full_name']}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_lead.inserted_id)


async def test__get_lead_id_by_field_route__returns_200_ok__when_sending_a_close_agent_name_match(lead_fixture, agent_fixture, lead_factory, agent_factory, test_client):
    lead = lead_fixture
    agent = agent_fixture
    inserted_agent = await agent_factory(**agent)
    lead["buyer_id"] = str(inserted_agent.inserted_id)
    lead["lead_sold_time"] = fake.date_time()
    inserted_lead = await lead_factory(**lead)
    response = test_client.get(f"/api/lead/find/?email={lead['email']}&buyer_name={agent['full_name'][:-1]}")
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_lead.inserted_id)


async def test__get_lead_id_by_field_route__returns_404_not_found__when_agent_name_is_sent_but_no_lead_exists(agent_fixture, agent_factory, test_client):
    agent = agent_fixture
    await agent_factory(**agent)
    response = test_client.get(f"/api/lead/find/?email={fake.email()}&buyer_name={agent['full_name']}")
    assert response.status_code == 404


async def test__get_lead_id_by_field_route__returns_404_not_found__when_agent_name_is_sent_but_no_agent_exists(lead_fixture, test_client):
    lead = lead_fixture
    response = test_client.get(f"/api/lead/find/?email={lead['email']}&buyer_name={fake.first_name()}")
    assert response.status_code == 404


async def test__get_lead_id_by_field_route__returns_422_unprocessable_entity__when_no_email_is_sent(test_client):
    response = test_client.get(f"/api/lead/find/")
    assert response.status_code == 422


async def test__get_lead_id_by_field_route__returns_422_unprocessable_entity__when_no_email_is_sent_but_agent_name_is_sent(test_client):
    response = test_client.get(f"/api/lead/find/?buyer_name={fake.first_name()}")
    assert response.status_code == 422


async def test__get_lead_id_by_field_route__returns_422_unprocessable_entity__when_no_email_is_sent_but_campaign_id_is_sent(test_client):
    response = test_client.get(f"/api/lead/find/?campaign_id={fake.random_number(digits=2)}")
    assert response.status_code == 422


async def test__get_lead_id_by_field_route__returns_422_unprocessable_entity__when_no_email_is_sent_but_agent_name_and_campaign_id_is_sent(test_client):
    response = test_client.get(f"/api/lead/find/?buyer_name={fake.first_name()}&campaign_id={fake.random_number(digits=2)}")
    assert response.status_code == 422


async def test__update_lead_from_ghl_route__returns_200_ok__when_lead_exists_in_database(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    updated_fields = {"created_time": str(fake.date_time()), "email": fake.email()}
    response = test_client.put(f"/api/lead/ghl/{inserted_lead.inserted_id}", json=updated_fields)
    assert response.status_code == 200
    assert response.json()['id'] == str(inserted_lead.inserted_id)


async def test__update_lead_from_ghl_route__returns_404_not_found__when_lead_does_not_exist_in_database(test_client):
    invalid_object_id = fake.hexify(text='^' * 24)
    updated_fields = {"created_time": str(fake.date_time()), "email": fake.email()}
    response = test_client.put(f"/api/lead/ghl/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 404
    assert response.json()['detail'] == f"Lead with id {invalid_object_id} not found"


async def test__update_lead_from_ghl_route__returns_400_lead_id_invalid__when_invalid_id_is_sent(test_client):
    invalid_object_id = fake.random_number(digits=12)
    updated_fields = {"created_time": str(fake.date_time()), "email": fake.email()}
    response = test_client.put(f"/api/lead/ghl/{invalid_object_id}", json=updated_fields)
    assert response.status_code == 400
    assert response.json()['detail'] == f"Invalid id {invalid_object_id} on update lead route"


async def test__update_lead_from_ghl_route__returns_400_empty_lead__when_no_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/ghl/{inserted_lead.inserted_id}", json={})
    assert response.status_code == 400


async def test__update_lead_from_ghl_route__returns_400_empty_lead__when_wrong_fields_are_sent(lead_fixture, lead_factory, test_client):
    lead = lead_fixture
    inserted_lead = await lead_factory(**lead)
    response = test_client.put(f"/api/lead/ghl/{inserted_lead.inserted_id}", json={"country": fake.country()})
    assert response.status_code == 400
