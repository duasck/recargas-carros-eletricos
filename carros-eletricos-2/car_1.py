import paho.mqtt.client as mqtt
import json
import random
import time
import logging

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = "vehicle/battery"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    logger.info(f"Car 1 connected to MQTT broker with code {rc}")

def simulate_vehicle():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    vehicle_id = "vehicle_1"
    battery_level = 100
    discharge_rate = "fast"  # Fast discharge
    rate_ranges = {"fast": (1.5, 3.0), "normal": (0.5, 2.0), "slow": (0.1, 0.5)}
    min_rate, max_rate = rate_ranges[discharge_rate]

    while True:
        battery_level -= random.uniform(min_rate, max_rate)
        if battery_level < 0:
            battery_level = 100  # Reset for continuous simulation
        payload = json.dumps({"vehicle_id": vehicle_id, "battery_level": round(battery_level, 2)})
        client.publish(mqtt_topic, payload)
        logger.info(f"Car 1 published: Battery {battery_level}%")
        time.sleep(5)

if __name__ == "__main__":
    simulate_vehicle()