import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import requests

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = "vehicle/battery"

# Server A endpoint for route planning
server_a_url = "http://server_a:5000/api/plan_route"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    logger.info(f"Car {userdata['vehicle_id']} connected to MQTT broker with code {rc}")

def request_recharge(vehicle_id):
    # Fixed route for simplicity (can be randomized)
    payload = {
        "start": "Salvador",
        "end": "Maceió",
        "vehicle_id": vehicle_id
    }
    # Optional: Randomize route
    # cities = ["Salvador", "Feira de Santana", "Aracaju", "Itabaiana", "Maceió", "Arapiraca"]
    # payload = {
    #     "start": random.choice(cities),
    #     "end": random.choice(cities),
    #     "vehicle_id": vehicle_id
    # }
    try:
        logger.info(f"Car {vehicle_id} requesting recharge: {payload}")
        response = requests.post(server_a_url, json=payload, timeout=5)
        response_data = response.json()
        logger.info(f"Car {vehicle_id} recharge response: {response_data}")
        return response_data
    except Exception as e:
        logger.error(f"Car {vehicle_id} failed to request recharge: {e}")
        return {"error": str(e)}

def simulate_vehicle(vehicle_id, discharge_rate):
    client = mqtt.Client(userdata={"vehicle_id": vehicle_id})
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    battery_level = 100
    rate_ranges = {"fast": (1.5, 3.0), "normal": (0.5, 2.0), "slow": (0.1, 0.5)}
    min_rate, max_rate = rate_ranges[discharge_rate]
    recharge_requested = False

    while True:
        battery_level -= random.uniform(min_rate, max_rate)
        if battery_level < 0:
            battery_level = 100  # Reset for continuous simulation
            recharge_requested = False

        payload = json.dumps({"vehicle_id": vehicle_id, "battery_level": round(battery_level, 2)})
        client.publish(mqtt_topic, payload)
        logger.info(f"Car {vehicle_id} published: Battery {battery_level}%")

        # Request recharge if battery <= 20% and not already requested
        if battery_level <= 20 and not recharge_requested:
            request_recharge(vehicle_id)
            recharge_requested = True  # Prevent multiple requests until reset

        time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python car.py <vehicle_id> <discharge_rate>")
        sys.exit(1)
    vehicle_id = sys.argv[1]
    discharge_rate = sys.argv[2]
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    simulate_vehicle(vehicle_id, discharge_rate)