from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import json
import logging
import threading
import networkx as nx

app = Flask(__name__)

# Adicionar lock global
charging_points_lock = threading.Lock()

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pontos de carga da empresa B (Sergipe)
charging_points = [
    {
        "id": "SE1",
        "location": "Aracaju",
        "capacity": 3,
        "reserved": 0,
        "queue": []
    },
    {
        "id": "SE2",
        "location": "Itabaiana",
        "capacity": 2,
        "reserved": 0,
        "queue": []
    }
]

# Grafo para roteamento
G = nx.Graph()
G.add_nodes_from(["Salvador", "Feira de Santana", "Aracaju", "Itabaiana", "Maceió", "Arapiraca"])
G.add_edges_from([
    ("Salvador", "Feira de Santana", {"weight": 100}),
    ("Feira de Santana", "Aracaju", {"weight": 300}),
    ("Aracaju", "Itabaiana", {"weight": 50}),
    ("Itabaiana", "Maceió", {"weight": 200}),
    ("Maceió", "Arapiraca", {"weight": 80})
])

# Configuração MQTT
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_client = mqtt.Client()

def on_mqtt_connect(client, userdata, flags, rc):
    logger.info(f"Server B connected to MQTT broker with code {rc}")
    client.subscribe("vehicle/server_b/battery")
    client.subscribe("charging/server_b/request")

def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
        if msg.topic == "vehicle/server_b/battery":
            logger.info(f"Battery update from {data['vehicle_id']}: {data['battery_level']}%")
            if data['battery_level'] < 20:
                threading.Thread(target=handle_low_battery, args=(data['vehicle_id'], data.get('current_city'))).start()
        
        elif msg.topic == "charging/server_b/request":
            logger.info(f"Charge request from {data['vehicle_id']}")
            handle_charge_request(data)
            
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

def handle_charge_request(data):
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
                        f"charging/{vehicle_id}/response",
                        json.dumps(response),
                        qos=1
                    )
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
                            f"charging/{next_vehicle}/response",
                            json.dumps({
                                "status": "READY",
                                "point_id": point_id,
                                "vehicle_id": next_vehicle
                            }),
                            qos=1
                        )
                    break

def handle_low_battery(vehicle_id, current_city, end_city):
    try:
        logger.info(f"Server A handling low battery for {vehicle_id} in {current_city}")
        
        # 1. Primeiro tenta resolver localmente (Bahia)
        local_points = [p for p in charging_points if p["location"] in ["Salvador", "Feira de Santana"]]
        
        for point in local_points:
            if point["reserved"] < point["capacity"]:
                point["reserved"] += 1
                mqtt_client.publish(
                    f"charging/{vehicle_id}/response",
                    json.dumps({
                        "status": "READY",
                        "point_id": point["id"],
                        "city": point["location"],
                        "server": "a",
                        "vehicle_id": vehicle_id
                    })
                )
                logger.info(f"Local reservation at {point['id']} for {vehicle_id}")
                return
            else:
                if vehicle_id not in point["queue"]:
                    point["queue"].append(vehicle_id)
                mqtt_client.publish(
                    f"charging/{vehicle_id}/response",
                    json.dumps({
                        "status": "QUEUED",
                        "point_id": point["id"],
                        "position": len(point["queue"]),
                        "city": point["location"],
                        "server": "a",
                        "vehicle_id": vehicle_id
                    })
                )
                logger.info(f"Added to queue at {point['id']} (position {len(point['queue'])})")
                return

        # 2. Planeja rota para outros pontos
        logger.info(f"Planning route from {current_city} to {end_city}")
        
        path = nx.shortest_path(G, current_city, end_city, weight="weight")
        logger.info(f"Calculated route: {path}")

        # 3. Verifica pontos no caminho
        for city in path[:-1]:
            for point in charging_points:
                if point["location"] == city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        mqtt_client.publish(
                            f"charging/{vehicle_id}/response",
                            json.dumps({
                                "status": "READY",
                                "point_id": point["id"],
                                "city": city,
                                "server": "a",
                                "vehicle_id": vehicle_id,
                                "route": path
                            })
                        )
                        return
                    else:
                        if vehicle_id not in point["queue"]:
                            point["queue"].append(vehicle_id)
                        mqtt_client.publish(
                            f"charging/{vehicle_id}/response",
                            json.dumps({
                                "status": "QUEUED",
                                "point_id": point["id"],
                                "position": len(point["queue"]),
                                "city": city,
                                "server": "a",
                                "vehicle_id": vehicle_id,
                                "route": path
                            })
                        )
                        return

        # 4. Se não encontrou nenhum ponto
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "UNAVAILABLE",
                "server": "a",
                "vehicle_id": vehicle_id,
                "message": "No charging points available along the route"
            })
        )

    except nx.NetworkXNoPath:
        error_msg = f"No path found from {current_city} to {end_city}"
        logger.error(error_msg)
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "NO_ROUTE",
                "server": "a",
                "vehicle_id": vehicle_id,
                "error": error_msg
            })
        )
    except Exception as e:
        error_msg = f"Server A error: {str(e)}"
        logger.error(error_msg)
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "ERROR",
                "server": "a",
                "vehicle_id": vehicle_id,
                "error": error_msg
            })
        )

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
                        f"charging/{vehicle_id}/response",
                        json.dumps(response),
                        qos=1
                    )
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
                            f"charging/{next_vehicle}/response",
                            json.dumps({
                                "status": "READY",
                                "point_id": point_id,
                                "vehicle_id": next_vehicle
                            }),
                            qos=1
                        )
                    break
def plan_route_for_vehicle(vehicle_id, start, end):
    logger.info(f"Server A: Planning route for vehicle {vehicle_id} from {start} to {end}")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"Server A: Shortest path: {path}")
        
        servers = {
            "company_a": "http://server_a:5000",
            "company_c": "http://server_c:5002"
        }
        reservations = []
        all_prepared = True
        
        # Phase 1: Prepare
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
            # Tentar Company A primeiro
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
                                break
            
            # Tentar outras empresas
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
                all_prepared = False
                break
        
        # Se falhou, abortar tudo
        if not all_prepared:
            for r in reservations:
                if r["company"] == "company_a":
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
                        logger.error(f"Server A: Error aborting reservation: {e}")
            
            mqtt_client.publish(
                f"charging/{vehicle_id}/response",
                json.dumps({
                    "status": "ERROR",
                    "server": "a",
                    "error": "Could not reserve all required points"
                })
            )
            return {"error": "Could not reserve all required points"}

        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_a":
                # Commit local
                for point in charging_points:
                    if point["id"] == r["point_id"] and "position" in r:
                        if vehicle_id in point["queue"]:
                            point["queue"].remove(vehicle_id)
                            point["reserved"] += 1
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
        
        # Notificar o carro
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "READY",
                "point_id": reservations[0]["point_id"],  # Primeiro ponto da rota
                "city": reservations[0]["city"],
                "server": "a",
                "route": path,
                "reservations": [{
                    "company": r["company"],
                    "point_id": r["point_id"],
                    "city": r["city"],
                    "position": r.get("position", 0)
                } for r in reservations]
            })
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
        logger.error(f"Server A: Route planning error: {e}")
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "ERROR",
                "server": "a",
                "error": str(e)
            })
        )
        return {"error": str(e)}



@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    return jsonify({
        "company_b": charging_points,
        "status": "success"
    })

@app.route('/api/queue_status/<point_id>', methods=['GET'])
def get_queue_status(point_id):
    for point in charging_points:
        if point['id'] == point_id:
            return jsonify({
                "reserved": point['reserved'],
                "queue_size": len(point['queue']),
                "queue": point['queue']
            })
    return jsonify({"error": "Point not found"}), 404


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
                if vehicle_id in point["queue"]:  # Idempotência
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

if __name__ == '__main__':
    # Configura MQTT
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()
    
    # Inicia servidor Flask
    app.run(host='0.0.0.0', port=5001)