from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import constants

# Adicionar lock global
charging_points_lock = threading.Lock()

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simulated database for Company E's charging points (Paraíba)
charging_points = [
    {
        "id": "PB1", 
        "location": "João Pessoa", 
        "capacity": 3,
        "reserved": 0,
        "queue": []
    },
    {
        "id": "PB2", 
        "location": "Campina Grande", 
        "capacity": 2,
        "reserved": 0,
        "queue": []
    }
]

# Graph for route planning
G = nx.Graph()
G.add_nodes_from([
    "Salvador", "Feira de Santana", "Aracaju", "Itabaiana", 
    "Maceió", "Arapiraca", "Recife", "Caruaru", 
    "João Pessoa", "Campina Grande"
])
G.add_edges_from([
    ("Salvador", "Feira de Santana", {"weight": 100}),
    ("Feira de Santana", "Aracaju", {"weight": 300}),
    ("Aracaju", "Itabaiana", {"weight": 50}),
    ("Itabaiana", "Maceió", {"weight": 200}),
    ("Maceió", "Arapiraca", {"weight": 80}),
    ("Maceió", "Recife", {"weight": 250}),
    ("Recife", "Caruaru", {"weight": 120}),
    ("Recife", "João Pessoa", {"weight": 110}),
    ("João Pessoa", "Campina Grande", {"weight": 130})
])

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = constants.TOPICO_BATERIA.format(server="server_e")

def handle_charging_request(data):
    vehicle_id = data["vehicle_id"]
    action = data["action"]
    
    with charging_points_lock:
        if action == "request":
            logger.info(f"Processing charge request from {vehicle_id}")
            for point in charging_points:
                if point["location"] == data["location"]:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        response = {
                            "status": "READY",
                            "point_id": point["id"],
                            "vehicle_id": vehicle_id
                        }
                    else:
                        if vehicle_id not in point["queue"]:
                            point["queue"].append(vehicle_id)
                        response = {
                            "status": "QUEUED",
                            "position": len(point["queue"]),
                            "vehicle_id": vehicle_id
                        }
                    mqtt_client.publish(
                        constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                        json.dumps(response),
                        qos=constants.MQTT_QOS
                    )
                    logger.info(f"Queue status for {point['id']} ({point['location']}): {point['queue']}")
                    break
        elif action == "done":
            point_id = data["point_id"]
            for point in charging_points:
                if point["id"] == point_id:
                    point["reserved"] = max(0, point["reserved"] - 1)
                    if point["queue"]:
                        next_vehicle = point["queue"].pop(0)
                        point["reserved"] += 1
                        mqtt_client.publish(
                            constants.TOPICO_RESPOSTA.format(vehicle_id=next_vehicle),
                            json.dumps({
                                "status": "READY",
                                "point_id": point_id,
                                "vehicle_id": next_vehicle
                            }),
                            qos=constants.MQTT_QOS
                        )
                    logger.info(f"Queue status for {point['id']} ({point['location']}): {point['queue']}")
                    break

def handle_low_battery(vehicle_id, current_city, end_city):
    try:
        logger.info(f"Server E handling low battery for {vehicle_id} in {current_city}")
        
        local_points = [p for p in charging_points if p["location"] in ["João Pessoa", "Campina Grande"]]
        
        for point in local_points:
            if point["reserved"] < point["capacity"]:
                point["reserved"] += 1
                mqtt_client.publish(
                    constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                    json.dumps({
                        "status": "READY",
                        "point_id": point["id"],
                        "city": point["location"],
                        "server": "e",
                        "vehicle_id": vehicle_id
                    }),
                    qos=constants.MQTT_QOS
                )
                logger.info(f"Local reservation at {point['id']} for {vehicle_id}")
                return
            else:
                if vehicle_id not in point["queue"]:
                    point["queue"].append(vehicle_id)
                mqtt_client.publish(
                    constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                    json.dumps({
                        "status": "QUEUED",
                        "point_id": point["id"],
                        "position": len(point["queue"]),
                        "city": point["location"],
                        "server": "e",
                        "vehicle_id": vehicle_id
                    }),
                    qos=constants.MQTT_QOS
                )
                logger.info(f"Added to queue at {point['id']} (position {len(point['queue'])})")
                return

        logger.info(f"Planning route from {current_city} to {end_city}")
        
        path = nx.shortest_path(G, current_city, end_city, weight="weight")
        logger.info(f"Calculated route: {path}")

        for city in path[:-1]:
            for point in charging_points:
                if point["location"] == city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        mqtt_client.publish(
                            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                            json.dumps({
                                "status": "READY",
                                "point_id": point["id"],
                                "city": city,
                                "server": "e",
                                "vehicle_id": vehicle_id,
                                "route": path
                            }),
                            qos=constants.MQTT_QOS
                        )
                        return
                    else:
                        if vehicle_id not in point["queue"]:
                            point["queue"].append(vehicle_id)
                        mqtt_client.publish(
                            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                            json.dumps({
                                "status": "QUEUED",
                                "point_id": point["id"],
                                "position": len(point["queue"]),
                                "city": city,
                                "server": "e",
                                "vehicle_id": vehicle_id,
                                "route": path
                            }),
                            qos=constants.MQTT_QOS
                        )
                        return

        mqtt_client.publish(
            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
            json.dumps({
                "status": "UNAVAILABLE",
                "server": "e",
                "vehicle_id": vehicle_id,
                "message": "No charging points available along the route"
            }),
            qos=constants.MQTT_QOS
        )

    except nx.NetworkXNoPath:
        error_msg = f"No path found from {current_city} to {end_city}"
        logger.error(error_msg)
        mqtt_client.publish(
            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
            json.dumps({
                "status": "NO_ROUTE",
                "server": "e",
                "vehicle_id": vehicle_id,
                "error": error_msg
            }),
            qos=constants.MQTT_QOS
        )
    except Exception as e:
        error_msg = f"Server E error: {str(e)}"
        logger.error(error_msg)
        mqtt_client.publish(
            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
            json.dumps({
                "status": "ERROR",
                "server": "e",
                "vehicle_id": vehicle_id,
                "error": error_msg
            }),
            qos=constants.MQTT_QOS
        )

def on_connect(client, userdata, flags, rc):
    logger.info(f"Server E connected to MQTT broker with code {rc}")
    client.subscribe(mqtt_topic)
    client.subscribe(constants.TOPICO_RESERVA.format(server="server_e"))

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
        if msg.topic == mqtt_topic:
            vehicle_id = data["vehicle_id"]
            battery_level = data["battery_level"]
            logger.info(f"Server E received battery update: {vehicle_id}, {battery_level}%")
            
            if battery_level < 30:
                threading.Thread(target=handle_low_battery, args=(vehicle_id, data.get("current_city"), data.get("end_city"))).start()
        
        elif msg.topic == constants.TOPICO_RESERVA.format(server="server_e"):
            handle_charging_request(data)
            
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    logger.info("Server E: Returning charging points")
    return jsonify({"company_e": charging_points})

@app.route('/api/prepare', methods=['POST'])
def prepare_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    if not point_id or not vehicle_id:
        return jsonify({"status": "ABORT"}), 400
    
    with charging_points_lock:
        for point in charging_points:
            if point["id"] == point_id:
                if vehicle_id in point["queue"]:
                    return jsonify({
                        "status": "QUEUED",
                        "position": point["queue"].index(vehicle_id) + 1,
                        "estimated_time": (point["queue"].index(vehicle_id) + 1) * 30
                    })
                if point["reserved"] < point["capacity"]:
                    point["reserved"] += 1
                    return jsonify({
                        "status": "READY",
                        "position": 0
                    })
                else:
                    point["queue"].append(vehicle_id)
                    return jsonify({
                        "status": "QUEUED",
                        "position": len(point["queue"]),
                        "estimated_time": len(point["queue"]) * 30
                    })
        return jsonify({"status": "ABORT"}), 400

@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    with charging_points_lock:
        for point in charging_points:
            if point["id"] == point_id:
                if vehicle_id in point["queue"]:
                    point["queue"].remove(vehicle_id)
                return jsonify({"status": "COMMITTED"})
        return jsonify({"status": "ABORTED"})

@app.route('/api/abort', methods=['POST'])
def abort_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    with charging_points_lock:
        for point in charging_points:
            if point["id"] == point_id:
                if vehicle_id in point["queue"]:
                    point["queue"].remove(vehicle_id)
                elif point["reserved"] > 0:
                    point["reserved"] -= 1
                    if point["queue"]:
                        next_vehicle = point["queue"].pop(0)
                        point["reserved"] += 1
                        mqtt_client.publish(
                            constants.TOPICO_RESPOSTA.format(vehicle_id=next_vehicle),
                            json.dumps({
                                "status": "READY",
                                "point_id": point_id,
                                "vehicle_id": next_vehicle
                            }),
                            qos=constants.MQTT_QOS
                        )
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
    logger.info(f"Server E: Planning route for vehicle {vehicle_id} from {start} to {end}")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"Server E: Shortest path: {path}")
        
        servers = {
            "company_a": constants.SERVERS["company_a"]["url"],
            "company_b": constants.SERVERS["company_b"]["url"],
            "company_c": constants.SERVERS["company_c"]["url"],
            "company_d": constants.SERVERS["company_d"]["url"]
        }
        reservations = []
        all_prepared = True
        
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
            for point in charging_points:
                if point["location"] == current_city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        reservations.append({
                            "company": "company_e",
                            "point_id": point["id"],
                            "city": current_city,
                            "url": None
                        })
                        reserved = True
                        logger.info(f"Server E: Prepared local reservation for {current_city}, point {point['id']}")
                        break
                    else:
                        prepare_response = requests.post(
                            constants.SERVERS["company_e"]["url"] + "/api/prepare",
                            json={"point_id": point["id"], "vehicle_id": vehicle_id},
                            timeout=2
                        )
                        if prepare_response.status_code == 200:
                            result = prepare_response.json()
                            if result["status"] == "QUEUED":
                                reservations.append({
                                    "company": "company_e",
                                    "point_id": point["id"],
                                    "city": current_city,
                                    "url": None,
                                    "position": result["position"]
                                })
                                reserved = True
                                break
            
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
                        logger.error(f"Server E: Error contacting {company}: {e}")
                        all_prepared = False
            
            if not reserved:
                all_prepared = False
                break
        
        if not all_prepared:
            for r in reservations:
                if r["company"] == "company_e":
                    for point in charging_points:
                        if point["id"] == r["point_id"]:
                            if "position" in r:
                                if vehicle_id in point["queue"]:
                                    point["queue"].remove(vehicle_id)
                            else:
                                point["reserved"] = max(0, point["reserved"] - 1)
                elif r["url"]:
                    try:
                        requests.post(
                            f"{r['url']}/api/abort",
                            json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
                            timeout=2
                        )
                    except Exception as e:
                        logger.error(f"Server E: Error aborting reservation: {e}")
            
            mqtt_client.publish(
                constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                json.dumps({
                    "status": "ERROR",
                    "server": "e",
                    "error": "Could not reserve all required points"
                }),
                qos=constants.MQTT_QOS
            )
            return {"error": "Could not reserve all required points"}

        for r in reservations:
            if r["company"] == "company_e":
                for point in charging_points:
                    if point["id"] == r["point_id"] and "position" in r:
                        if vehicle_id in point["queue"]:
                            point["queue"].remove(vehicle_id)
                            point["reserved"] += 1
                logger.info(f"Server E: Committed local reservation for {r['city']}, point {r['point_id']}")
            elif r["url"]:
                try:
                    requests.post(
                        f"{r['url']}/api/commit",
                        json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
                        timeout=2
                    )
                except Exception as e:
                    logger.error(f"Server E: Error committing reservation: {e}")
        
        mqtt_client.publish(
            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
            json.dumps({
                "status": "READY",
                "point_id": reservations[0]["point_id"],
                "city": reservations[0]["city"],
                "server": "e",
                "route": path,
                "reservations": [{
                    "company": r["company"],
                    "point_id": r["point_id"],
                    "city": r["city"],
                    "position": r.get("position", 0)
                } for r in reservations]
            }),
            qos=constants.MQTT_QOS
        )
        
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
        logger.error(f"Server E: Route planning error: {e}")
        mqtt_client.publish(
            constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
            json.dumps({
                "status": "ERROR",
                "server": "e",
                "error": str(e)
            }),
            qos=constants.MQTT_QOS
        )
        return {"error": str(e)}

@app.route('/api/plan_route', methods=['POST'])
def plan_route():
    data = request.json
    start = data.get("start")
    end = data.get("end")
    vehicle_id = data.get("vehicle_id")
    
    if not start or not end or not vehicle_id:
        logger.error("Server E: Missing start, end, or vehicle_id")
        return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
    
    result = plan_route_for_vehicle(vehicle_id, start, end)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=constants.SERVIDOR_E)