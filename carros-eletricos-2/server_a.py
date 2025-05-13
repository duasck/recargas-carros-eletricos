from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import time

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
<<<<<<< Updated upstream
mqtt_topic = "vehicle/battery"
=======
mqtt_topic = "vehicle/server_a/battery"

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

def check_atomic_availability(vehicle_id, path):
    """Verifica a disponibilidade atômica em todos os pontos da rota"""
    logger.info(f"🚀 Iniciando verificação atômica para veículo {vehicle_id} na rota: {path}")
    reservations = []
    all_available = True
    
    for city in path[:-1]:  # Não precisa verificar a cidade final
        logger.info(f"🔍 Verificando disponibilidade em {city}...")
        reserved = False
        
        # Primeiro verifica pontos locais
        for point in charging_points:
            if point["location"] == city:
                if point["reserved"] < point["capacity"]:
                    logger.info(f"  ✅ Ponto LOCAL disponível: {point['id']} em {city}")
                    reservations.append({
                        "company": "company_a",
                        "point_id": point["id"],
                        "city": city,
                        "url": None,
                        "status": "READY"
                    })
                    reserved = True
                    break
                else:
                    if len(point["queue"]) < 3:
                        logger.info(f"  ⏳ Ponto LOCAL com fila: {point['id']} (posição {len(point['queue']) + 1})")
                        reservations.append({
                            "company": "company_a",
                            "point_id": point["id"],
                            "city": city,
                            "url": None,
                            "status": "QUEUED",
                            "position": len(point["queue"]) + 1
                        })
                        reserved = True
                        break
        
        # Se não encontrou localmente, verifica outros servidores
        if not reserved:
            for company, info in SERVERS.items():
                if company == "company_a":
                    continue
                
                if city in info["cities"]:
                    try:
                        logger.info(f"  🔄 Consultando servidor {company} para {city}...")
                        response = requests.get(
                            f"{info['url']}/api/check_availability",
                            params={"city": city, "vehicle_id": vehicle_id},
                            timeout=2
                        )
                        if response.status_code == 200:
                            result = response.json()
                            if result["status"] in ["READY", "QUEUED"]:
                                logger.info(f"    ✔️ {company} respondeu: {result['status']}")
                                reservations.append({
                                    "company": company,
                                    "point_id": result["point_id"],
                                    "city": city,
                                    "url": info["url"],
                                    "status": result["status"],
                                    "position": result.get("position", 0)
                                })
                                reserved = True
                                break
                    except Exception as e:
                        logger.error(f"    ❌ Erro ao consultar {company}: {e}")
                        all_available = False
                        break
        
        if not reserved:
            logger.warning(f"  ❗ Nenhum ponto disponível em {city}")
            all_available = False
            break
    
    logger.info(f"🔚 Resultado da verificação atômica: {'SUCESSO' if all_available else 'FALHA'}")
    return all_available, reservations

@app.route('/api/check_availability', methods=['GET'])
def check_availability():
    """Endpoint para verificar disponibilidade em uma cidade específica"""
    city = request.args.get("city")
    vehicle_id = request.args.get("vehicle_id")
    
    if not city or not vehicle_id:
        return jsonify({"error": "Missing city or vehicle_id"}), 400
    
    with charging_points_lock:
        for point in charging_points:
            if point["location"] == city:
                if point["reserved"] < point["capacity"]:
                    return jsonify({
                        "status": "READY",
                        "point_id": point["id"],
                        "city": city
                    })
                else:
                    if len(point["queue"]) < 3:  # Limite máximo de fila
                        return jsonify({
                            "status": "QUEUED",
                            "point_id": point["id"],
                            "city": city,
                            "position": len(point["queue"]) + 1
                        })
        
        return jsonify({"status": "UNAVAILABLE"}), 404

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
>>>>>>> Stashed changes

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
connect_mqtt()
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
    logger.info(f"\n\n📡📡📡 INÍCIO DO PLANEJAMENTO ATÔMICO PARA {vehicle_id} ({start} → {end}) 📡📡📡")
    try:
        path = nx.shortest_path(G, start, end, weight="weight")
        logger.info(f"🗺️  Rota calculada: {' → '.join(path)}")

        # Fase 1: Verificação atômica
        all_available, reservations = check_atomic_availability(vehicle_id, path)
        
<<<<<<< Updated upstream
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
=======
        if not all_available:
            logger.warning("⛔ Falha na verificação atômica - pontos indisponíveis")
            mqtt_client.publish(
                f"charging/{vehicle_id}/response",
                json.dumps({
                    "status": "UNAVAILABLE",
                    "server": "a",
                    "error": "Not all charging points available along the route"
                })
            )
            return {"error": "Not all charging points available along the route"}
        
        logger.info("✅ Todos os pontos confirmados. Iniciando commit das reservas...")
        
        # Fase 2: Reserva real (commit)
        for r in reservations:
            if r["company"] == "company_a":
                with charging_points_lock:
                    for point in charging_points:
                        if point["id"] == r["point_id"]:
                            if r["status"] == "READY":
                                logger.info(f"  🔒 Reservando localmente: {point['id']} (READY)")
                                point["reserved"] += 1
                            else:  # QUEUED
                                logger.info(f"  🔒 Adicionando na fila local: {point['id']} (posição {r.get('position')})")
                                point["queue"].append(vehicle_id)
            else:
                try:
                    logger.info(f"  🔄 Confirmando reserva em {r['company']} ({r['point_id']})...")
                    response = requests.post(
                        f"{r['url']}/api/commit",
                        json={
                            "point_id": r["point_id"],
                            "vehicle_id": vehicle_id,
                            "status": r["status"]
                        },
                        timeout=2
                    )
                    if response.status_code != 200:
                        logger.error(f"    ❌ Falha ao confirmar em {r['company']}")
                except Exception as e:
                    logger.error(f"    ❌ Erro ao confirmar em {r['company']}: {e}")
        
        logger.info(f"🎉 Todas as reservas confirmadas! Notificando veículo {vehicle_id}")
        
        # Notifica o veículo
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "READY",
                "point_id": reservations[0]["point_id"],
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
        
        logger.info(f"📡📡📡 FIM DO PLANEJAMENTO ATÔMICO PARA {vehicle_id} 📡📡📡\n\n")
        return {
            "path": path,
            "reservations": reservations
        }
    except Exception as e:
        logger.error(f"Server A: Error {e}")
>>>>>>> Stashed changes

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