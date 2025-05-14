import pytest
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
import paho.mqtt.client
import car
import generic_server
import constants

@pytest.fixture
def server_config():
    return {
        "company": "company_a",
        "name": "a",
        "port": constants.SERVIDOR_A,
        "charging_points": [
            {"id": "BA1", "location": "Salvador", "capacity": 2, "reserved": 0, "queue": []}
        ]
    }

@pytest.fixture
def mqtt_client():
    client = paho.mqtt.client.Client()
    client.connect("broker.hivemq.com", 1883, 60)
    client.loop_start()
    yield client
    client.loop_stop()
    client.disconnect()

def test_high_concurrency_reservations(server_config):
    app, port = generic_server.create_server(server_config)
    num_cars = 5
    results = []

    def request_reservation(vehicle_id):
        data = {
            "vehicle_id": vehicle_id,
            "action": "request",
            "location": "Salvador"
        }
        with app.app_context():
            with patch("generic_server.mqtt_client") as mock_mqtt:
                generic_server.handle_charging_request(data)
                results.append(json.loads(mock_mqtt.publish.call_args[0][1]))

    with ThreadPoolExecutor(max_workers=num_cars) as executor:
        futures = [executor.submit(request_reservation, f"vehicle_{i}") for i in range(num_cars)]
        for future in futures:
            future.result()

    ready_count = sum(1 for r in results if r["status"] == "READY")
    queued_count = sum(1 for r in results if r["status"] == "QUEUED")
    assert ready_count == 2  # Capacity is 2
    assert queued_count == 3  # Remaining cars are queued

def test_server_failure_recovery(server_config, mqtt_client):
    app, port = generic_server.create_server(server_config)
    vehicle_id = "vehicle_1"
    data = {
        "vehicle_id": vehicle_id,
        "action": "request",
        "location": "Salvador"
    }

    # Simulate server failure
    with patch("generic_server.mqtt_client.connect") as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")
        with app.app_context():
            generic_server.handle_charging_request(data)
            # No publish should occur due to failure
            assert not mqtt_client.publish.called

    # Simulate recovery
    with patch("generic_server.mqtt_client") as mock_mqtt:
        with app.app_context():
            generic_server.handle_charging_request(data)
            mock_mqtt.publish.assert_called_once()
            published_data = json.loads(mock_mqtt.publish.call_args[0][1])
            assert published_data["status"] == "READY"

def test_critical_battery_condition():
    vehicle_id = "vehicle_1"
    discharge_rate = "fast"
    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 5.0,  # Critical battery level
        "current_city": "Salvador",
        "recharge_status": None,
        "discharge_rate": discharge_rate,
        "logger": MagicMock(),
        "route": ["Salvador", "Feira de Santana"],
        "current_city_index": 0,
        "reservations": {}
    }

    with patch("car.plan_route") as mock_plan_route:
        mock_plan_route.return_value = {
            "path": ["Salvador", "Feira de Santana"],
            "reservations": [{"company": "company_a", "point_id": "BA1", "city": "Salvador"}]
        }
        with patch("car.mqtt.Client") as mock_mqtt:
            car.simulate_vehicle(vehicle_id, discharge_rate)
            mock_plan_route.assert_called_once()
            # Ensure car prioritizes charging due to low battery
            assert mock_mqtt.return_value.publish.called