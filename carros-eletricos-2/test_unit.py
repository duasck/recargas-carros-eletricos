import pytest
import json
from unittest.mock import patch, MagicMock
import constants
import car
import generic_server
import networkx as nx

@pytest.fixture
def mock_mqtt_client():
    client = MagicMock()
    client.publish = MagicMock()
    client.subscribe = MagicMock()
    return client

@pytest.fixture
def mock_requests():
    with patch("requests.post") as mock_post, patch("requests.get") as mock_get:
        yield {"post": mock_post, "get": mock_get}

def test_plan_route_success(mock_requests):
    vehicle_id = "vehicle_1"
    start_city = "Salvador"
    end_city = "Recife"
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "path": ["Salvador", "Feira de Santana", "Aracaju", "Maceió", "Recife"],
        "reservations": [
            {"company": "company_a", "point_id": "BA1", "city": "Salvador", "position": 0}
        ]
    }
    mock_requests["post"].return_value = mock_response

    result = car.plan_route(vehicle_id, start_city, end_city)
    assert result == mock_response.json.return_value
    mock_requests["post"].assert_called_once()

def test_plan_route_failure(mock_requests):
    vehicle_id = "vehicle_1"
    start_city = "Salvador"
    end_city = "Recife"
    
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    mock_requests["post"].return_value = mock_response

    result = car.plan_route(vehicle_id, start_city, end_city)
    assert "error" in result
    assert result["error"] == "Failed to plan route"

def test_handle_charging_request_ready():
    server_config = {
        "company": "company_a",
        "name": "a",
        "port": constants.SERVIDOR_A,
        "charging_points": [
            {"id": "BA1", "location": "Salvador", "capacity": 2, "reserved": 0, "queue": []}
        ]
    }
    app, port = generic_server.create_server(server_config)
    with app.app_context():
        data = {
            "vehicle_id": "vehicle_1",
            "action": "request",
            "location": "Salvador"
        }
        with patch("generic_server.mqtt_client") as mock_mqtt:
            generic_server.handle_charging_request(data)
            mock_mqtt.publish.assert_called_once()
            published_data = json.loads(mock_mqtt.publish.call_args[0][1])
            assert published_data["status"] == "READY"
            assert published_data["point_id"] == "BA1"
            assert server_config["charging_points"][0]["reserved"] == 1

def test_handle_charging_request_queued():
    server_config = {
        "company": "company_a",
        "name": "a",
        "port": constants.SERVIDOR_A,
        "charging_points": [
            {"id": "BA1", "location": "Salvador", "capacity": 1, "reserved": 1, "queue": []}
        ]
    }
    app, port = generic_server.create_server(server_config)
    with app.app_context():
        data = {
            "vehicle_id": "vehicle_1",
            "action": "request",
            "location": "Salvador"
        }
        with patch("generic_server.mqtt_client") as mock_mqtt:
            generic_server.handle_charging_request(data)
            mock_mqtt.publish.assert_called_once()
            published_data = json.loads(mock_mqtt.publish.call_args[0][1])
            assert published_data["status"] == "QUEUED"
            assert published_data["position"] == 1
            assert server_config["charging_points"][0]["queue"] == ["vehicle_1"]

def test_battery_consumption():
    G = nx.Graph()
    G.add_edge("Salvador", "Feira de Santana", weight=100)
    distance = G["Salvador"]["Feira de Santana"]["weight"]
    battery_level = 100.0
    discharge_rate = "fast"
    battery_drain = distance * constants.BATTERY_CONSUMPTION[discharge_rate]
    new_battery_level = max(0.1, battery_level - battery_drain)
    assert new_battery_level == 80.0  # 100 - (100 * 0.2) = 80