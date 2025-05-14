import pytest
import time
from concurrent.futures import ThreadPoolExecutor
import generic_server
import constants
import json
from unittest.mock import patch

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

def test_reservation_latency(server_config):
    app, port = generic_server.create_server(server_config)
    num_requests = 10
    latencies = []

    def make_request(vehicle_id):
        start_time = time.time()
        data = {
            "vehicle_id": f"vehicle_{vehicle_id}",
            "action": "request",
            "location": "Salvador"
        }
        with app.app_context():
            with patch("generic_server.mqtt_client") as mock_mqtt:
                generic_server.handle_charging_request(data)
        return time.time() - start_time

    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        latencies = list(executor.map(make_request, range(num_requests)))

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 0.1, f"Average latency {avg_latency:.3f}s is too high"

def test_reservation_success_rate(server_config):
    app, port = generic_server.create_server(server_config)
    num_requests = 10
    results = []

    def make_request(vehicle_id):
        data = {
            "vehicle_id": f"vehicle_{vehicle_id}",
            "action": "request",
            "location": "Salvador"
        }
        with app.app_context():
            with patch("generic_server.mqtt_client") as mock_mqtt:
                generic_server.handle_charging_request(data)
                return json.loads(mock_mqtt.publish.call_args[0][1])

    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        results = list(executor.map(make_request, range(num_requests)))

    success_count = sum(1 for r in results if r["status"] in ["READY", "QUEUED"])
    success_rate = success_count / num_requests
    assert success_rate >= 0.9, f"Success rate {success_rate:.2%} is too low"