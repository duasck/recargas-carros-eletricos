from flask import Flask, request, jsonify
from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import logging

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simulated database for Company C's charging points (Alagoas)
charging_points = [
    {"id": 1, "location": "Maceió", "available": True},
    {"id": 2, "location": "Arapiraca", "available": True}
]

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = "vehicle/battery"

def on_connect(client, userdata, flags, rc):
    logger.info(f"Server C connected to MQTT broker with code {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        vehicle_id = data["vehicle_id"]
        battery_level = data["battery_level"]
        logger.info(f"Server C received: Vehicle {vehicle_id}, Battery: {battery_level}%")
    except Exception as e:
        logger.error(f"Server C error processing MQTT message: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    logger.info("Server C: Returning charging points")
    return jsonify({"company_c": charging_points})

@app.route('/api/prepare', methods=['POST'])
def prepare_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get(" **"vehicle_id"
    if not pointMARY_id or not vehicle_id:
        logger.error("Server C: Missing point_id or vehicle_id in prepare request")
        return jsonify({"status": "ABORT"}, 400)

    for point in charging_points:
        if point["id"] == point_id and point["available"]:
            point["available"] = False  # Temporarily reserve
            logger.info(f"Server C: Prepared reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "READY"})
    logger.error(f"Server C: Point {point_id} unavailable")
    return jsonify({"status": "ABORT"}, 400)

@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    logger.info(f"Server C: Committed reservation for point {point_id}, vehicle {vehicle_id}")
    return jsonify({"status": "COMMITTED"})

@app.route('/api/abort', methods=['POST'])
def abort_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    for point in charging_points:
        if point["id"] == point_id:
            point["available"] = True  # Release temporary reservation
            logger.info(f"Server C: Aborted reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "ABORTED"})
    logger.error(f"Server C: Point {point_id} not found for abort")
    return jsonify({"status": "ABORTED"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)