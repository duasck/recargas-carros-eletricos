from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
<<<<<<< Updated upstream

app = Flask(__name__)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
=======
import time

app = Flask(__name__)

# Logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
>>>>>>> Stashed changes
logger = logging.getLogger(__name__)
 
charging_points = [
<<<<<<< Updated upstream
    {"id": "AL1", "location": "Maceió", "available": True},
    {"id": "AL2", "location": "Arapiraca", "available": True}
=======
    {
        "id": "BA1", 
        "location": "Maceió", 
        "capacity": 3,  # Número máximo de carros simultâneos
        "reserved": 0,  # Carros atualmente reservados
        "queue": []     # Fila de espera
    },
    {
        "id": "BA2", 
        "location": "Arapiraca", 
        "capacity": 2,
        "reserved": 0,
        "queue": []
    }
>>>>>>> Stashed changes
]

# Lock para threads
charging_points_lock = threading.Lock()

# Configuração MQTT
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
<<<<<<< Updated upstream
mqtt_topic = "vehicle/battery"
=======
mqtt_topic = "vehicle/server_c/battery"
>>>>>>> Stashed changes

mqtt_client = mqtt.Client()

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

def on_connect(client, userdata, flags, rc):
    logger.info(f"Server C conectado ao broker MQTT com código {rc}")
    client.subscribe(mqtt_topic)

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
<<<<<<< Updated upstream
        vehicle_id = data["vehicle_id"]
        battery_level = data["battery_level"]
        logger.info(f"Server C received: Vehicle {vehicle_id}, Battery: {battery_level}%")
    except Exception as e:
        logger.error(f"Server C error processing MQTT message: {e}")

mqtt_client = mqtt.Client()
=======
        
        if msg.topic == "vehicle/server_c/battery":
            logger.info(f"Atualização de bateria: {data['vehicle_id']} - {data['battery_level']}%")
            if data['battery_level'] < 20:
                threading.Thread(target=handle_low_battery, args=(data['vehicle_id'], data.get('current_city'))).start()
        
        elif msg.topic == "charging/server_c/request":
            handle_charge_request(data)
            
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")

>>>>>>> Stashed changes
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

if not connect_mqtt():
    logger.error("Falha crítica na conexão MQTT. Encerrando.")
    exit(1)

mqtt_client.loop_start()

@app.route('/api/charging_points', methods=['GET'])
def get_charging_points():
    logger.info("Server C: Returning charging points")
    return jsonify({"company_c": charging_points})

@app.route('/api/prepare', methods=['POST'])
def prepare_reservation():
    data = request.json
    point_id = data.get("point_id")
    vehicle_id = data.get("vehicle_id")
    if not point_id or not vehicle_id:
<<<<<<< Updated upstream
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

=======
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
    
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
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


>>>>>>> Stashed changes
def plan_route_for_vehicle(vehicle_id, start, end):
    logger.info(f"Server C: Planning route for vehicle {vehicle_id} from {start} to {end}")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"Server C: Shortest path: {path}")
        
        servers = {
            "company_a": "http://server_a:5000",
            "company_b": "http://server_b:5001"
        }
        reservations = []
        
        # Phase 1: Prepare
        for i in range(len(path) - 1):
            current_city = path[i]
            reserved = False
            
<<<<<<< Updated upstream
            # Try Company C (local)
            for point in charging_points:
                if point["location"] == current_city and point["available"]:
                    point["available"] = False
                    reservations.append({"company": "company_c", "point_id": point["id"]})
                    reserved = True
                    logger.info(f"Server C: Prepared local reservation for {current_city}, point {point['id']}")
                    break
=======
            # Tenta Company C primeiro
            for point in charging_points:
                if point["location"] == current_city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        reservations.append({
                            "company": "company_c",
                            "point_id": point["id"],
                            "city": current_city,
                            "url": None
                        })
                        reserved = True
                        logger.info(f"Server C: Prepared local reservation for {current_city}, point {point['id']}")
                        break
                    else:
                        prepare_response = requests.post(
                            "http://server_c:5002/api/prepare",
                            json={"point_id": point["id"], "vehicle_id": vehicle_id},
                            timeout=2
                        )
                        if prepare_response.status_code == 200:
                            result = prepare_response.json()
                            if result["status"] == "QUEUED":
                                reservations.append({
                                    "company": "company_c",
                                    "point_id": point["id"],
                                    "city": current_city,
                                    "url": None,
                                    "position": result["position"]
                                })
                                reserved = True
                                break
>>>>>>> Stashed changes
            
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
                                    logger.info(f"Server C: Prepared reservation with {company} for {current_city}, point {point['id']}")
                                    break
                        if reserved:
                            break
                    except Exception as e:
                        logger.error(f"Server C: Error contacting {company}: {e}")
<<<<<<< Updated upstream
=======
                        all_prepared = False
>>>>>>> Stashed changes
            
            if not reserved:
                logger.error(f"Server C: No available points for {current_city}")
                # Phase 2: Abort
                for r in reservations:
                    if r["company"] == "company_c":
                        for point in charging_points:
                            if point["id"] == r["point_id"]:
                                point["available"] = True
                    else:
                        requests.post(f"{servers[r['company']]}/api/abort", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server C: Aborted all reservations for vehicle {vehicle_id}")
                return {"error": f"No available points for {current_city}"}
        
<<<<<<< Updated upstream
        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_c":
                logger.info(f"Server C: Committed local reservation for point {r['point_id']}")
            else:
                requests.post(f"{servers[r['company']]}/api/commit", json={"point_id": r["point_id"], "vehicle_id": vehicle_id})
                logger.info(f"Server C: Committed reservation with {r['company']} for point {r['point_id']}")
=======
        # Se falhou, abortar tudo
        if not all_prepared:
            for r in reservations:
                if r["company"] == "company_c":
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
                        logger.error(f"Server C: Error aborting reservation: {e}")
            
            mqtt_client.publish(
                f"charging/{vehicle_id}/response",
                json.dumps({
                    "status": "ERROR",
                    "server": "c",
                    "error": "Could not reserve all required points"
                })
            )
            return {"error": "Could not reserve all required points"}

        # Phase 2: Commit
        for r in reservations:
            if r["company"] == "company_c":
                # Commit local
                for point in charging_points:
                    if point["id"] == r["point_id"] and "position" in r:
                        if vehicle_id in point["queue"]:
                            point["queue"].remove(vehicle_id)
                            point["reserved"] += 1
                logger.info(f"Server C: Committed local reservation for {r['city']}, point {r['point_id']}")
            elif r["url"]:
                try:
                    requests.post(
                        f"{r['url']}/api/commit",
                        json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
                        timeout=2
                    )
                except Exception as e:
                    logger.error(f"Server C: Error committing reservation: {e}")
        
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
>>>>>>> Stashed changes
        
        logger.info(f"Server C: Route planning successful for vehicle {vehicle_id}: {path}")
        return {"path": path, "reservations": reservations}
    except Exception as e:
        logger.error(f"Server C: Route planning error: {e}")
<<<<<<< Updated upstream
        return {"error": "Route planning failed"}
=======
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "ERROR",
                "server": "c",
                "error": str(e)
            })
        )
        return {"error": str(e)}


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
>>>>>>> Stashed changes

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

@app.route('/api/plan_route', methods=['POST'])
def plan_route():
    data = request.json
    start = data.get("start")
    end = data.get("end")
    vehicle_id = data.get("vehicle_id")
    
    if not start or not end or not vehicle_id:
        logger.error("Server C: Missing start, end, or vehicle_id")
        return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
    
    result = plan_route_for_vehicle(vehicle_id, start, end)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)