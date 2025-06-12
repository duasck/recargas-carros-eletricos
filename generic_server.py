from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import constants
import os
from ecdsa import SigningKey, SECP256k1
from hashlib import sha256

try:
    from blockchain.ledger import registrar_transacao, register_identity, deposit
except ImportError:
    registrar_transacao = None
    register_identity = None
    deposit = None

def create_server(server_config):
    company_name = server_config['company']
    server_name = server_config['name']
    port = server_config['port']
    charging_points = server_config['charging_points']
    company_account = server_config['account']

    charging_points_lock = threading.Lock()

    app = Flask(__name__)

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(f'Server_{server_name.upper()}')

    G = nx.Graph()
    G.add_nodes_from(constants.CITYS_NODES)
    G.add_edges_from(constants.CITYS_WEIGHT)

    mqtt_broker = "broker.hivemq.com"
    mqtt_port = constants.PORTA_MQTT
    mqtt_topic_battery = constants.TOPICO_BATERIA.format(server=f"server_{server_name}")
    mqtt_topic_request = constants.TOPICO_RESERVA.format(server=f"server_{server_name}")

    def verify_signature(message, signature, public_key):
        try:
            sk = SigningKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
            vk = sk.verifying_key
            return vk.verify(bytes.fromhex(signature), message.encode())
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def handle_charging_request(data):
        vehicle_id = data['vehicle_id']
        action = data['action']
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{action}", signature, public_key):
            logger.error(f"Invalid signature for {vehicle_id}")
            return

        with charging_points_lock:
            if action == 'request':
                logger.info(f'Processing charge request from {vehicle_id}')
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

                        logger.info(f"Queue status for [{point['id']}]-({point['location']}): {point['queue']}")
                        break

            elif action == "done":
                point_id = data["point_id"]
                for point in charging_points:
                    if point["id"] == point_id:
                        point["reserved"] = max(0, point["reserved"] - 1)
                        logger.info(f"Point {point_id} at {point['location']} released by {vehicle_id}, reserved: {point['reserved']}")
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
                            logger.info(f"Notified next vehicle {next_vehicle} for point {point_id}")
                        logger.info(f"Queue status for {point['id']} ({point['location']}): {point['queue']}")
                        break

        if registrar_transacao:
            try:
                tx_hash = registrar_transacao('recarga', {'vehicle_id': vehicle_id, 'action': action, 'status': 'INICIO'}, company_account, company_account)
                logger.info(f'Transação blockchain registrada: tipo=recarga, dados={{"vehicle_id": "{vehicle_id}", "action": "{action}", "status": "INICIO"}}, tx_hash={tx_hash}')
            except Exception as e:
                logger.warning(f'Erro ao registrar recarga no blockchain: {e}')

    def handle_route_request(data):
        vehicle_id = data['vehicle_id']
        city_start = data['start']
        city_end = data['end']
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{city_start}{city_end}", signature, public_key):
            logger.error(f"Invalid signature for {vehicle_id}")
            return

        logger.info(f'{server_name.upper()}: Received route request from {vehicle_id}:\n        Start: {city_start} ====> End: {city_end}')

        result = plan_route_for_vehicle(vehicle_id, city_start, city_end)
        
        response_topic = constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id)
        if 'error' in result:
            response = {'status': "ERROR", 'error': result['error']}
        else:
            response = {'status': 'READY', 'route': result['path'], 'reservations': result['reservations']}

        mqtt_client.publish(response_topic, json.dumps(response), qos=constants.MQTT_QOS)
        logger.info(f"{server_name.upper()}: Sent route response to {vehicle_id}")    def on_connect(client, userdata, flags, rc, properties=None):
        logger.info(f"{server_name.upper()} connected to MQTT broker with code {rc}")
        client.subscribe(mqtt_topic_battery)
        client.subscribe(mqtt_topic_request)
        client.subscribe(constants.TOPICO_ROUTE_REQUEST.format(server=f"server_{server_name}"))

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            if msg.topic == mqtt_topic_request:
                handle_charging_request(data)
            elif msg.topic == constants.TOPICO_ROUTE_REQUEST.format(server=f"server_{server_name}"):
                handle_route_request(data)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    # mqtt_client = mqtt.Client()
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()

    @app.route('/api/charging_points', methods=['GET'])
    def list_charging_points():
        logger.info(f'{server_name.upper()}: returning charging points')
        return jsonify({company_name: charging_points})

    @app.route('/api/prepare', methods=['POST'])
    def prepare_reservation():
        data = request.json
        point_id = data.get("point_id")
        vehicle_id = data.get("vehicle_id")
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
            return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

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
                        logger.info(f"Server {server_name.upper()}: Prepared reservation for {vehicle_id} at {point_id}")
                        if registrar_transacao:
                            try:
                                tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'PREPARE'}, company_account, company_account)
                                logger.info(f'Transação blockchain registrada: tipo=reserva, dados={{"point_id": "{point_id}", "vehicle_id": "{vehicle_id}", "status": "PREPARE"}}, tx_hash={tx_hash}')
                            except Exception as e:
                                logger.warning(f'Erro ao registrar no blockchain: {e}')
                        return jsonify({
                            "status": "READY",
                            "position": 0
                        })
                    else:
                        point["queue"].append(vehicle_id)
                        logger.info(f"Server {server_name.upper()}: Queued {vehicle_id} at {point_id}, position {len(point['queue'])}")
                        return jsonify({
                            "status": "QUEUED",
                            "position": len(point["queue"]),
                            "estimated_time": len(point["queue"]) * 30
                        })
            return jsonify({"status": "ABORT"}), 400

    @app.route('/api/commit', methods=['POST'])
    def commit_reservation():
        data = request.json
        point_id = data.get('point_id')
        vehicle_id = data.get('vehicle_id')
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
            return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

        with charging_points_lock:
            for point in charging_points:
                if point['id'] == point_id:
                    if vehicle_id in point['queue']:
                        point['queue'].remove(vehicle_id)
                        point['reserved'] += 1
                    logger.info(f'{server_name.upper()}: Committed reservation for {vehicle_id} in {point_id}')
                    if registrar_transacao:
                        try:
                            tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'COMMIT'}, company_account, company_account)
                            logger.info(f'Transação blockchain registrada: tipo=reserva, dados={{"point_id": "{point_id}", "vehicle_id": "{vehicle_id}", "status": "COMMIT"}}, tx_hash={tx_hash}')
                        except Exception as e:
                            logger.warning(f'Erro ao registrar no blockchain: {e}')
                    return jsonify({'status': 'COMMITTED'})

    @app.route('/api/abort', methods=['POST'])
    def abort_reservation():
        data = request.json
        point_id = data.get("point_id")
        vehicle_id = data.get("vehicle_id")
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
            return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

        with charging_points_lock:
            for point in charging_points:
                if point["id"] == point_id:
                    if vehicle_id in point["queue"]:
                        point["queue"].remove(vehicle_id)
                        logger.info(f"{server_name.upper()}: Aborted queue reservation for {vehicle_id} at {point_id}")
                    elif point["reserved"] > 0:
                        point["reserved"] -= 1
                        logger.info(f"{server_name.upper()}: Aborted reservation for {vehicle_id} at {point_id}, reserved: {point['reserved']}")
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
                            logger.info(f"Server {server_name.upper()}: Notified next vehicle {next_vehicle} for point {point_id}")
                    if registrar_transacao:
                        try:
                            tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'ABORT'}, company_account, company_account)
                            logger.info(f'Transação blockchain registrada: tipo=reserva, dados={{"point_id": "{point_id}", "vehicle_id": "{vehicle_id}", "status": "ABORT"}}, tx_hash={tx_hash}')
                        except Exception as e:
                            logger.warning(f'Erro ao registrar no blockchain: {e}')
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

    @app.route('/api/payment', methods=['POST'])
    def process_payment():
        data = request.json
        vehicle_id = data.get('vehicle_id')
        amount_wei = data.get('amount')
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not vehicle_id or not amount_wei or not signature or not public_key:
            return jsonify({"status": "ERROR", "error": "Missing parameters"}), 400

        if not verify_signature(f"{vehicle_id}{amount_wei}", signature, public_key):
            return jsonify({"status": "ERROR", "error": "Invalid signature"}), 400

        try:
            tx_hash = registrar_transacao(
                'pagamento',
                {'vehicle_id': vehicle_id, 'amount': amount_wei, 'status': 'COMPLETED'},
                company_account, # A empresa registra a transação
                company_account, # O valor vai para a empresa (se o contrato transferir)
                amount_wei
            )
            logger.info(f"Payment processed for {vehicle_id}: {amount_wei} wei, tx_hash={tx_hash}")
            return jsonify({"status": "COMPLETED", "tx_hash": tx_hash})
        except Exception as e:
            logger.error(f"Payment failed for {vehicle_id}: {e}")
            return jsonify({"status": "ERROR", "error": str(e)}), 400

    def plan_route_for_vehicle(vehicle_id, start, end):
        logger.info(f"{server_name.upper()}: Planning route for vehicle {vehicle_id} [{start} => {end}]")
        try:
            path = nx.shortest_path(G, start, end, weight="weight")
            logger.info(f"{server_name.upper()}: Shortest path: [{path}]")
            
            servers = {
                s["company"]: constants.SERVERS[s["company"]]["url"]
                for s in constants.servers_port
                if s["company"] != company_name
            }
            reservations = []
            all_prepared = True
            
            for i in range(len(path)):
                current_city = path[i]
                reserved = False
                
                for point in charging_points:
                    if point["location"] == current_city:
                        if point["reserved"] < point["capacity"]:
                            point["reserved"] += 1
                            reservations.append({
                                "company": company_name,
                                "point_id": point["id"],
                                "city": current_city,
                                "url": None
                            })
                            reserved = True
                            logger.info(f"{server_name.upper()}: Prepared local reservation for {current_city}, point {point['id']}")
                            break
                        else:
                            prepare_response = requests.post(
                                constants.SERVERS[company_name]["url"] + "/api/prepare",
                                json={"point_id": point["id"], "vehicle_id": vehicle_id, "signature": "dummy", "public_key": "dummy"},
                                timeout=2
                            )
                            if prepare_response.status_code == 200:
                                result = prepare_response.json()
                                if result["status"] == "QUEUED":
                                    reservations.append({
                                        "company": company_name,
                                        "point_id": point["id"],
                                        "city": current_city,
                                        "url": None,
                                        "position": result["position"]
                                    })
                                    reserved = True
                                    break
                
                if not reserved:
                    for other_company, url in servers.items():
                        try:
                            response = requests.get(f"{url}/api/charging_points", timeout=2)
                            if response.status_code == 200:
                                points = response.json().get(other_company, [])
                                for point in points:
                                    if point["location"] == current_city:
                                        prepare_response = requests.post(
                                            f"{url}/api/prepare",
                                            json={"point_id": point["id"], "vehicle_id": vehicle_id, "signature": "dummy", "public_key": "dummy"},
                                            timeout=2
                                        )
                                        if prepare_response.status_code == 200:
                                            result = prepare_response.json()
                                            if result["status"] == "READY":
                                                reservations.append({
                                                    "company": other_company,
                                                    "point_id": point["id"],
                                                    "city": current_city,
                                                    "url": url
                                                })
                                                reserved = True
                                                break
                                            elif result["status"] == "QUEUED":
                                                reservations.append({
                                                    "company": other_company,
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
                            logger.error(f"{server_name.upper()}: Error contacting {other_company}: {e}")
                            all_prepared = False
                
                if not reserved:
                    all_prepared = False
                    break
            
            if not all_prepared:
                for r in reservations:
                    if r["company"] == company_name:
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
                                json={"point_id": r["point_id"], "vehicle_id": vehicle_id, "signature": "dummy", "public_key": "dummy"},
                                timeout=2
                            )
                        except Exception as e:
                            logger.error(f"{server_name.upper()}: Error aborting reservation: {e}")
                
                mqtt_client.publish(
                    constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                    json.dumps({
                        "status": "ERROR",
                        "server": server_name,
                        "error": "Could not reserve all required points"
                    }),
                    qos=constants.MQTT_QOS
                )
                return {"error": "Could not reserve all required points"}

            for r in reservations:
                if r["company"] == company_name:
                    for point in charging_points:
                        if point["id"] == r["point_id"] and "position" in r:
                            if vehicle_id in point["queue"]:
                                point["queue"].remove(vehicle_id)
                                point["reserved"] += 1
                    logger.info(f"{server_name.upper()}: Committed local reservation for {r['city']}, point {r['point_id']}")
                elif r["url"]:
                    try:
                        requests.post(
                            f"{r['url']}/api/commit",
                            json={"point_id": r["point_id"], "vehicle_id": vehicle_id, "signature": "dummy", "public_key": "dummy"},
                            timeout=2
                        )
                    except Exception as e:
                        logger.error(f"{server_name.upper()}: Error committing reservation: {e}")
            
            mqtt_client.publish(
                constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                json.dumps({
                    "status": "READY",
                    "point_id": reservations[0]["point_id"],
                    "city": reservations[0]["city"],
                    "server": server_name,
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
            logger.error(f"Server {server_name.upper()}: Route planning error: {e}")
            mqtt_client.publish(
                constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id),
                json.dumps({
                    "status": "ERROR",
                    "server": server_name,
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
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not signature or not public_key or not verify_signature(f"{vehicle_id}{start}{end}", signature, public_key):
            return jsonify({"status": "ERROR", "error": "Invalid signature"}), 400
        
        if not start or not end or not vehicle_id:
            logger.error(f"Server {server_name.upper()}: Missing start, end, or vehicle_id")
            return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
        
        result = plan_route_for_vehicle(vehicle_id, start, end)
        return jsonify(result)

    return app, port

if __name__ == '__main__':
    print('Working')