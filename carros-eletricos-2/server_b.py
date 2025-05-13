from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
<<<<<<< Updated upstream
=======
import networkx as nx
import time
>>>>>>> Stashed changes

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

<<<<<<< Updated upstream
# Simulated database for Company B's charging points (Sergipe)
=======
def connect_mqtt():
    max_retries = 5
    retry_delay = 3  # segundos
    
    for attempt in range(max_retries):
        try:
            mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            logger.info("Conexão MQTT bem-sucedida!")
            return True
        except Exception as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    logger.error("Não foi possível conectar ao MQTT após várias tentativas.")
    return False

# Pontos de carga da empresa B (Sergipe)
>>>>>>> Stashed changes
charging_points = [
    {"id": "SE1", "location": "Aracaju", "available": True},
    {"id": "SE2", "location": "Itabaiana", "available": True}
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
    logger.info(f"Server B connected to MQTT broker with code {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        vehicle_id = data["vehicle_id"]
        battery_level = data["battery_level"]
        logger.info(f"Server B received: Vehicle {vehicle_id}, Battery: {battery_level}%")
    except Exception as e:
<<<<<<< Updated upstream
        logger.error(f"Server B error processing MQTT message: {e}")
=======
        logger.error(f"Error processing MQTT message: {e}")

@app.route('/api/check_availability', methods=['GET'])
def check_availability():
    """Endpoint para verificar disponibilidade em uma cidade específica"""
    city = request.args.get("city")
    vehicle_id = request.args.get("vehicle_id")
    
    logger.info(f"\n🔎 Recebida consulta de disponibilidade para {vehicle_id} em {city}")
    
    if not city or not vehicle_id:
        return jsonify({"error": "Missing city or vehicle_id"}), 400
    
    with charging_points_lock:
        for point in charging_points:
            if point["location"] == city:
                if point["reserved"] < point["capacity"]:
                    logger.info(f"  ✅ Ponto {point['id']} disponível (READY)")
                    return jsonify({
                        "status": "READY",
                        "point_id": point["id"],
                        "city": city
                    })
                else:
                    if len(point["queue"]) < 3:
                        pos = len(point["queue"]) + 1
                        logger.info(f"  ⏳ Ponto {point['id']} com fila (posição {pos})")
                        return jsonify({
                            "status": "QUEUED",
                            "point_id": point["id"],
                            "city": city,
                            "position": pos
                        })
        
        logger.info(f"  ❌ Nenhum ponto disponível em {city}")
        return jsonify({"status": "UNAVAILABLE"}), 404

@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    status = data.get("status")
    
    logger.info(f"\n📝 Recebido commit para {vehicle_id} no ponto {point_id} ({status})")
    
    if not point_id or not vehicle_id or not status:
        return jsonify({"error": "Missing required fields"}), 400
    
    with charging_points_lock:
        for point in charging_points:
            if point["id"] == point_id:
                if status == "READY":
                    logger.info(f"  🔒 Reservando ponto {point_id} para {vehicle_id}")
                    point["reserved"] += 1
                elif status == "QUEUED":
                    logger.info(f"  📥 Adicionando {vehicle_id} na fila do ponto {point_id}")
                    if vehicle_id not in point["queue"]:
                        point["queue"].append(vehicle_id)
                return jsonify({"status": "COMMITTED"})
    
    logger.warning(f"  ❌ Ponto {point_id} não encontrado")
    return jsonify({"error": "Point not found"}), 404

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
        logger.info(f"Server B handling low battery for {vehicle_id} in {current_city}")
        
        # 1. Primeiro tenta resolver localmente (Bahia)
        local_points = [p for p in charging_points if p["location"] in ["Aracaju", "Itabaiana"]]
        
        for point in local_points:
            if point["reserved"] < point["capacity"]:
                point["reserved"] += 1
                mqtt_client.publish(
                    f"charging/{vehicle_id}/response",
                    json.dumps({
                        "status": "READY",
                        "point_id": point["id"],
                        "city": point["location"],
                        "server": "b",
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
                        "server": "b",
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
                                "server": "b",
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
                                "server": "b",
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
                "server": "b",
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
                "server": "b",
                "vehicle_id": vehicle_id,
                "error": error_msg
            })
        )
    except Exception as e:
        error_msg = f"Server B error: {str(e)}"
        logger.error(error_msg)
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "ERROR",
                "server": "b",
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

>>>>>>> Stashed changes

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(mqtt_broker, mqtt_port, 60)
mqtt_client.loop_start()

@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    logger.info("Server B: Returning charging points")
    return jsonify({"company_b": charging_points})

@app.route('/api/prepare', methods=['POST'])
def prepare_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    
    if not point_id or not vehicle_id:
        logger.error("Server B: Missing point_id or vehicle_id in prepare request")
        return jsonify({"status": "ABORT"}), 400
    
    for point in charging_points:
        if point["id"] == point_id and point["available"]:
            point["available"] = False  # Temporarily reserve
            logger.info(f"Server B: Prepared reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "READY"})
    logger.error(f"Server B: Point {point_id} unavailable")
    return jsonify({"status": "ABORT"}), 400

<<<<<<< Updated upstream
@app.route('/api/commit', methods=['POST'])
def commit_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    logger.info(f"Server B: Committed reservation for point {point_id}, vehicle {vehicle_id}")
    return jsonify({"status": "COMMITTED"})

@app.route('/api/abort', methods=['POST'])
def abort_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
=======
if __name__ == '__main__':
    # Configura MQTT
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    connect_mqtt()
    mqtt_client.loop_start()
>>>>>>> Stashed changes
    
    for point in charging_points:
        if point["id"] == point_id:
            point["available"] = True  # Release temporary reservation
            logger.info(f"Server B: Aborted reservation for point {point_id}, vehicle {vehicle_id}")
            return jsonify({"status": "ABORTED"})
    logger.error(f"Server B: Point {point_id} not found for abort")
    return jsonify({"status": "ABORTED"})

def plan_route_for_vehicle(vehicle_id, start, end):
    logger.info(f"Server B: Planning route for vehicle {vehicle_id} from {start} to {end}")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"Server B: Shortest path: {path}")
        
        servers = {
            "company_a": "http://server_a:5000",
            "company_c": "http://server_c:5002"
        }
        reservations = []
        
        # Phase 1: Prepare
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
            # Try Company B (local)
            for point in charging_points:
                if point["location"] == current_city and point["available"]:
                    point["available"] = False
                    reservations.append({"company": "company_b", "point_id": point["id"]})
                    reserved = True
                    logger.info(f"Server B: Prepared local reservation for {current_city}, point {point['id']}")
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
                                    logger.info(f"Server B: Prepared reservation with {company} for {current_city}, point {point['id']}")
                                    break
                        if reserved:
                            break
                    except Exception as e:
                        logger.error(f"Server B: Error contacting {company}: {e}")
            
            if not reserved:
                logger.error(f"Server B: No available points for {current_city}")
                # Phase 2: Abort
                for r in reservations:
                    if r["company"] == "company_b":
                        for point in charging_points:
                            if point["id"] == r["point_id"]:
                                point["available"] = True
                    else:
                        requests.post(f"{servers[r['company']]}/api/abort", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server B: Aborted all reservations for vehicle {vehicle_id}")
                return {"error": f"No available points for {current_city}"}
        
        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_b":
                logger.info(f"Server B: Committed local reservation for point {r['point_id']}")
            else:
                requests.post(f"{servers[r['company']]}/api/commit", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server B: Committed reservation with {r['company']} for point {r['point_id']}")
        
        logger.info(f"Server B: Route planning successful for vehicle {vehicle_id}: {path}")
        return {"path": path, "reservations": reservations}
    except Exception as e:
        logger.error(f"Server B: Route planning error: {e}")
        return {"error": "Route planning failed"}

@app.route('/api/plan_route', methods=['POST'])
def plan_route():
    data = request.json
    start = data.get("start")
    end = data.get("end")
    vehicle_id = data.get("vehicle_id")
    
    if not start or not end or not vehicle_id:
        logger.error("Server B: Missing start, end, or vehicle_id")
        return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
    
    result = plan_route_for_vehicle(vehicle_id, start, end)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)