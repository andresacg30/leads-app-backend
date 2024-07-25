def test_create_agent(test_client):
    agent = {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "janedodc@example.com",
                "phone": "555-555-5555",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"]
            }
    response = test_client.post("/api/agent/", json=agent)
    assert response.status_code == 201


def test__create_agent_route__returns_409_exists__if_agent_exists_in_campaigns():
    agent = {
                "first_name": "Jane",
                "last_name": "Doe",
                "states_with_license": ["CA", "NY"],
                "CRM": {
                    "name": "Ringy",
                    "url": "www.ringy.com",
                    "integration_details": {
                        "auth_token": "value1",
                        "sid": "value2"
                        }
                },
                "credentials": {
                    "username": "value1",
                    "password": "value2"
                },
                "campaigns": ["5f9c0a9e9c6d4b1e9c6d4b1e"]
            }
    response = client.post("/api/agent/", json=agent)
    assert response.status_code == 405
    

