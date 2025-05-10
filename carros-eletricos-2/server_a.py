from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simulated database for Company A's charging points (Bahia)
charging_points = [
    {"id": "BA1", "location": "Salvador", "available": True},
    {"id": "BA2", "location": "Feira de Santana", "available": True}
]

# Graph for route planning
G = nx.Graph()
G.add_nodes_from(["Salvador", "Feira de Santana", "Aracaju", "Itabaiana", "Maceió", "Arapiraca"])
G.add_edges_from([
    ("Salvador", "Feira de Santana", {"weight": 100}),
    ("Feira de Santana", "Aracaju", {"weight": 300}),
    ("Aracaju", "Itabaiana", {"weight": 50}),
    ("Itabaiana", "Maceió", {"weight": 200}),
    ("Maceió", "Arapiraca", {"weight": 80})
])

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = "vehicle/battery"

def on_connect(client, userdata, flags, rc):
    logger.info(f"Server A connected to MQTT broker with code {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        vehicle_id = data["vehicle_id"]
        battery_level = data["battery_level"]
        logger.info(f"Server A received: Vehicle {vehicle_id}, Battery: {battery_level}%")
        # Automatically trigger route planning for low battery
        if battery_level < 30:
            threading.Thread(target=plan_route_for_vehicle, args=(vehicle_id, "Salvador", "Maceió")).start()
    except Exception as e:
        logger.error(f"Server A error processing MQTT message: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    logger.info("Server A: Returning charging points")
    return jsonify({"company_a": charging_points})

@app.route('/api/prepare', methods=['POST'])
def prepare_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    if not point_id or not vehicle_id:
        logger.error("Server A: Missing point_id or vehicle_id in prepare request")
        return jsonify({"status": "ABORT"}), 400
    
    for point in charging_points:
        if point["id"] == point_id and point["available"]:
            point["available"] = False  # Temporarily reserve
            logger.info(f"Server A: Prepared reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "READY"})
    logger.error(f"Server A: Point {point_id} unavailable")
    return jsonify({"status": "ABORT"}), 400

@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    logger.info(f"Server A: Committed reservation for point {point_id}, vehicle {vehicle_id}")
    return jsonify({"status": "COMMITTED"})

@app.route('/api/abort', methods=['POST'])
def abort_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    for point in charging_points:
        if point["id"] == point_id:
            point["available"] = True  # Release temporary reservation
            logger.info(f"Server A: Aborted reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "ABORTED"})
    logger.error(f"Server A: Point {point_id} not found for abort")
    return jsonify({"status": "ABORTED"})

def plan_route_for_vehicle(vehicle_id, start, end):
    logger.info(f"Server A: Planning route for vehicle {vehicle_id} from {start} to {end}")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"Server A: Shortest path: {path}")
        
        servers = {
            "company_b": "http://server_b:5001",
            "company_c": "http://server_c:5002"
        }
        reservations = []
        
        # Phase 1: Prepare
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
            # Try Company A (local)
            for point in charging_points:
                if point["location"] == current_city and point["available"]:
                    point["available"] = False
                    reservations.append({"company": "company_a", "point_id": point["id"]})
                    reserved = True
                    logger.info(f"Server A: Prepared local reservation for {current_city}, point {point['id']}")
                    break
            
            # Try other companies
            if not reserved:
                for company, url in servers.items():
                    try:
                        response = requests.get(f"{url}/api/charging_points")
                        points = response.json()[company]
                        for point in points:
                            if point["location"] == current_city and point["available"]:
                                prepare_response = requests.post(f"{url}/api/prepare", json={"point_id": point["id"], "vehicle_id": vehicle_id})
                                if prepare_response.json()["status"] == "READY":
                                    reservations.append({"company": company, "point_id": point["id"]})
                                    reserved = True
                                    logger.info(f"Server A: Prepared reservation with {company} for {current_city}, point {point['id']}")
                                    break
                        if reserved:
                            break
                    except Exception as e:
                        logger.error(f"Server A: Error contacting {company}: {e}")
            
            if not reserved:
                logger.error(f"Server A: No available points for {current_city}")
                # Phase 2: Abort
                for r in reservations:
                    if r["company"] == "company_a":
                        for point in charging_points:
                            if point["id"] == r["point_id"]:
                                point["available"] = True
                    else:
                        requests.post(f"{servers[r['company']]}/api/abort", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server A: Aborted all reservations for vehicle {vehicle_id}")
                return {"error": f"No available points for {current_city}"}
        
        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_a":
                logger.info(f"Server A: Committed local reservation for point {r['point_id']}")
            else:
                requests.post(f"{servers[r['company']]}/api/commit", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server A: Committed reservation with {r['company']} for point {r['point_id']}")
        
        logger.info(f"Server A: Route planning successful for vehicle {vehicle_id}: {path}")
        return {"path": path, "reservations": reservations}
    except Exception as e:
        logger.error(f"Server A: Route planning error: {e}")
        return {"error": "Route planning failed"}

@app.route('/api/plan_route', methods=['POST'])
def plan_route():
    data = request.json
    start = data.get("start")
    end = data.get("end")
    vehicle_id = data.get("vehicle_id")
    
    if not start or not end or not vehicle_id:
        logger.error("Server A: Missing start, end, or vehicle_id")
        return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
    
    result = plan_route_for_vehicle(vehicle_id, start, end)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)