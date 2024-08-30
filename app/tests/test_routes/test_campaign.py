import datetime
import time
import freezegun
import pytest

from bson import ObjectId
from app.controllers.campaign import get_campaign_collection


async def test__create_campaign_route__returns_200__when_creating_campaign_that_does_not_exist(campaign_fixture, test_client):
    campaign = campaign_fixture
    response = test_client.post("api/campaign/", json=campaign)
    assert response.status_code == 201
    assert "id" in response.json()
    assert await get_campaign_collection().find_one({"_id": ObjectId(response.json()["id"])}) is not None


async def test__create_campaign_route__returns_400__when_creating_campaign_that_already_exists(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    await campaign_factory(**campaign)
    response = test_client.post("api/campaign/", json=campaign)
    assert response.status_code == 400
    assert f"Campaign {campaign['name']} already exists" == response.json()["detail"]


@pytest.mark.parametrize("field", ["name", "active"])
async def test__create_campaign_route__returns_422_unprocessable_entity__when_missing_required_field(field, campaign_fixture, test_client):
    campaign = campaign_fixture
    del campaign[field]
    response = test_client.post("api/campaign/", json=campaign)
    assert response.status_code == 422


async def test__list_campaigns_route__returns_200_ok__when_campaigns_exist_in_database(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    await campaign_factory(**campaign)
    response = test_client.get("/api/campaign/?sort=id=ASC")
    assert response.status_code == 200
    assert len(response.json()['data']) > 0
    assert response.json()['total'] > 0


async def test__list_campaigns_route__returns_200_ok__when_campaigns_do_not_exist_in_database(test_client):
    response = test_client.get("/api/campaign/")
    assert response.status_code == 200
    assert len(response.json()['data']) == 0


async def test__list_campaigns_route__returns_200_ok__when_more_than_one_campaign_exists_in_database(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    second_campaign = campaign_fixture
    await campaign_factory(**campaign)
    await campaign_factory(**second_campaign)
    response = test_client.get("/api/campaign/")
    assert response.status_code == 200
    assert len(response.json()['data']) > 1


async def test__list_campaigns_route_returns_200_ok_and_sorted_by_id__when_sort_query_is_valid(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    await campaign_factory(**campaign)
    await campaign_factory(**campaign)
    response = test_client.get("/api/campaign/?sort=id=ASC")
    assert response.status_code == 200
    assert response.json()['data'][0]['id'] < response.json()['data'][1]['id']


@freezegun.freeze_time('2021-01-01')
async def test__list_campaigns_route_returns_200_ok_and_correctly_sorted__when_sort_query_is_start_date(campaign_fixture, campaign_factory, test_client):
    now_time = datetime.datetime.now()
    campaign = campaign_fixture

    campaign["start_date"] = now_time
    await campaign_factory(**campaign)
    await campaign_factory(use_fixture_model=True, start_date=now_time + datetime.timedelta(days=1))
    response = test_client.get("/api/campaign/?sort=start_date=ASC")
    assert response.status_code == 200
    assert response.json()['data'][0]['start_date'] < response.json()['data'][1]['start_date']


async def test__list_campaigns_route__returns_only_1_campaign__when_limit_query_is_1(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    await campaign_factory(**campaign)
    await campaign_factory(use_fixture_model=True)
    response = test_client.get("/api/campaign/?limit=1")
    assert response.status_code == 200
    assert len(response.json()['data']) == 1


@freezegun.freeze_time('2021-01-01')
async def test__list_campaigns_route__returns_last_campaign__when_page_query_is_2(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    inserted_campaign = await campaign_factory(**campaign)
    time.sleep(1)
    second_inserted_campaign = await campaign_factory(use_fixture_model=True)
    time.sleep(1)

    response = test_client.get("/api/campaign/?page=2&limit=1&sort_by=created_at")

    assert response.status_code == 200
    assert len(response.json()['data']) == 1
    assert response.json()['data'][0]['id'] == str(second_inserted_campaign.inserted_id)
    assert response.json()['data'][0]['id'] != str(inserted_campaign.inserted_id)


async def test_list_campaign_rout__returns_correct_campaign__when_filter_is_name(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    inserted_campaign = await campaign_factory(**campaign)
    second_inserted_campaign = await campaign_factory(use_fixture_model=True)
    response = test_client.get("/api/campaign/?filter={\"name\":\"%s\"}" % campaign['name'])
    assert response.status_code == 200
    assert response.json()['data'][0]['name'] == campaign['name']
    assert response.json()['data'][0]['id'] == str(inserted_campaign.inserted_id)
    assert len(response.json()['data']) == 1
    assert second_inserted_campaign.inserted_id not in [campaign['id'] for campaign in response.json()['data']]


@pytest.mark.skip(reason="Need to change the way the filter is being passed when filtering by dates")
@freezegun.freeze_time('2021-01-01')
async def test__list_campaigns_route__returns_campaigns__when_filter_is_created_time(campaign_fixture, campaign_factory, test_client):
    campaign = campaign_fixture
    campaign['created_time'] = datetime.datetime.now()
    inserted_campaign = await campaign_factory(**campaign)
    second_inserted_campaign = await campaign_factory(use_fixture_model=True, created_time=datetime.datetime.now() - datetime.timedelta(days=1))
    response = test_client.get("/api/campaign/?filter={\"created_time\":\"%s\"}" % campaign['created_time'])
    assert response.status_code == 200
    assert response.json()['data'][0]['id'] == str(inserted_campaign.inserted_id)
    assert len(response.json()['data']) == 1
    assert second_inserted_campaign.inserted_id not in [campaign['id'] for campaign in response.json()['data']]


async def test__list_campaigns_route__returns_400_bad_request__when_sort_query_is_invalid(test_client):
    response = test_client.get("/api/campaign/?sort=id=INVALID")
    assert response.status_code == 400
