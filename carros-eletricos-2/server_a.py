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
    {
        "id": "BA1", 
        "location": "Salvador", 
        "capacity": 3,  # Número máximo de carros simultâneos
        "reserved": 0,  # Carros atualmente reservados
        "queue": []     # Fila de espera
    },
    {
        "id": "BA2", 
        "location": "Feira de Santana", 
        "capacity": 2,
        "reserved": 0,
        "queue": []
    }
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
#mqtt_topic = "vehicle/battery"
mqtt_topic = "vehicle/server_a/battery"

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
        return jsonify({"status": "ABORT"}), 400
    
    for point in charging_points:
        if point["id"] == point_id:
            if point["reserved"] < point["capacity"]:
                point["reserved"] += 1
                return jsonify({
                    "status": "READY",
                    "position": 0  # Entra direto no posto
                })
            else:
                # Adiciona na fila
                position = len(point["queue"]) + 1
                point["queue"].append(vehicle_id)
                return jsonify({
                    "status": "QUEUED",
                    "position": position,
                    "estimated_time": position * 30  # 30 minutos por carro
                })
    return jsonify({"status": "ABORT"}), 400

@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    for point in charging_points:
        if point["id"] == point_id:
            # Se estava na fila, remove
            if vehicle_id in point["queue"]:
                point["queue"].remove(vehicle_id)
            return jsonify({"status": "COMMITTED"})
    return jsonify({"status": "ABORTED"})

@app.route('/api/abort', methods=['POST'])
def abort_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    for point in charging_points:
        if point["id"] == point_id:
            if vehicle_id in point["queue"]:
                point["queue"].remove(vehicle_id)
            elif point["reserved"] > 0:
                point["reserved"] -= 1
                # Libera vaga para próximo da fila
                if point["queue"]:
                    next_vehicle = point["queue"].pop(0)
                    point["reserved"] += 1
                    # Notificar o próximo veículo (implementar lógica MQTT)
            return jsonify({"status": "ABORTED"})
    return jsonify({"status": "ABORTED"})

@app.route('/api/queue_status/<point_id>', methods=['GET'])
def queue_status(point_id):
    for point in charging_points:
        if point["id"] == point_id:
            return jsonify({
                "reserved": point["reserved"],
                "queue_size": len(point["queue"]),
                "queue": point["queue"]
            })
    return jsonify({"error": "Point not found"}), 404

@app.route('/api/charging_status', methods=['GET'])
def charging_status():
    status = []
    for point in charging_points:
        status.append({
            "id": point["id"],
            "location": point["location"],
            "reserved": point["reserved"],
            "queue_size": len(point["queue"]),
            "queue": point["queue"]
        })
    return jsonify(status)

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
        all_prepared = True
        
        # Phase 1: Prepare
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
            # Try Company A (local) first
            for point in charging_points:
                if point["location"] == current_city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        reservations.append({
                            "company": "company_a",
                            "point_id": point["id"],
                            "city": current_city,
                            "url": None
                        })
                        reserved = True
                        logger.info(f"Server A: Prepared local reservation for {current_city}, point {point['id']}")
                        break
                    else:
                        # Try to queue
                        prepare_response = requests.post(
                            "http://server_a:5000/api/prepare",
                            json={"point_id": point["id"], "vehicle_id": vehicle_id},
                            timeout=2
                        )
                        if prepare_response.status_code == 200:
                            result = prepare_response.json()
                            if result["status"] == "QUEUED":
                                reservations.append({
                                    "company": "company_a",
                                    "point_id": point["id"],
                                    "city": current_city,
                                    "url": None,
                                    "position": result["position"]
                                })
                                reserved = True
                                logger.info(f"Server A: Added to queue for {current_city}, point {point['id']}")
                                break
            
            # Try other companies if needed
            if not reserved:
                for company, url in servers.items():
                    try:
                        response = requests.get(f"{url}/api/charging_points", timeout=2)
                        if response.status_code == 200:
                            points = response.json().get(company, [])
                            for point in points:
                                if point["location"] == current_city:
                                    prepare_response = requests.post(
                                        f"{url}/api/prepare",
                                        json={"point_id": point["id"], "vehicle_id": vehicle_id},
                                        timeout=2
                                    )
                                    if prepare_response.status_code == 200:
                                        result = prepare_response.json()
                                        if result["status"] == "READY":
                                            reservations.append({
                                                "company": company,
                                                "point_id": point["id"],
                                                "city": current_city,
                                                "url": url
                                            })
                                            reserved = True
                                            break
                                        elif result["status"] == "QUEUED":
                                            reservations.append({
                                                "company": company,
                                                "point_id": point["id"],
                                                "city": current_city,
                                                "url": url,
                                                "position": result["position"]
                                            })
                                            reserved = True
                                            break
                            if reserved:
                                break
                    except Exception as e:
                        logger.error(f"Server A: Error contacting {company}: {e}")
                        all_prepared = False
            
            if not reserved:
                logger.error(f"Server A: No available points for {current_city}")
                all_prepared = False
                break
        
        # If any failed, abort all
        if not all_prepared:
            logger.info(f"Server A: Aborting all reservations for vehicle {vehicle_id}")
            for r in reservations:
                if r["company"] == "company_a":
                    for point in charging_points:
                        if point["id"] == r["point_id"]:
                            if "position" in r:  # Was in queue
                                if r["vehicle_id"] in point["queue"]:
                                    point["queue"].remove(r["vehicle_id"])
                            else:  # Was reserved
                                point["reserved"] = max(0, point["reserved"] - 1)
                elif r["url"]:
                    try:
                        requests.post(
                            f"{r['url']}/api/abort",
                            json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
                            timeout=2
                        )
                    except Exception as e:
                        logger.error(f"Server A: Error aborting reservation: {e}")
            
            return {"error": "Could not reserve all required points"}

        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_a":
                logger.info(f"Server A: Committed local reservation for {r['city']}, point {r['point_id']}")
            elif r["url"]:
                try:
                    requests.post(
                        f"{r['url']}/api/commit",
                        json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
                        timeout=2
                    )
                except Exception as e:
                    logger.error(f"Server A: Error committing reservation: {e}")
        
        return {
            "path": path,
            "reservations": [{
                "company": r["company"],
                "point_id": r["point_id"],
                "city": r["city"],
                "position": r.get("position", 0)
            } for r in reservations]
        }
        
    except Exception as e:
        logger.error(f"Server A: Route planning error: {e}")
        return {"error": str(e)}
 
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