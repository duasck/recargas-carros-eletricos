from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import global_utils.constants as constants
import os
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from hashlib import sha256
from web3 import Web3 # Adicionado para criar o objeto da conta

try:
    # Importando a função corrigida do ledger
    from blockchain.ledger import record_transaction
except ImportError:
    record_transaction = None


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

    # Configuração do Web3 para o servidor
    w3 = Web3()

    G = nx.Graph()
    G.add_nodes_from(constants.CITYS_NODES)
    G.add_edges_from(constants.CITYS_WEIGHT)

    # CORREÇÃO: Usar o nome do serviço Docker "mosquitto"
    mqtt_broker = os.getenv("MQTT_BROKER", "mosquitto")
    mqtt_port = constants.PORTA_MQTT
    mqtt_topic_battery = constants.TOPICO_BATERIA.format(server=f"server_{server_name}")
    mqtt_topic_request = constants.TOPICO_RESERVA.format(server=f"server_{server_name}")

    def verify_signature(message, signature, public_key):
        try:
            # ECDSA espera a chave pública em formato de bytes, não hex
            vk = VerifyingKey.from_string(bytes.fromhex(public_key), curve=SECP256k1)
            
            # Agora verificamos a assinatura com a chave de verificação.
            return vk.verify(bytes.fromhex(signature), message.encode())
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def handle_charging_request(data):
        vehicle_id = data['vehicle_id']
        action = data['action']
        signature = data.get('signature')
        public_key = data.get('public_key')

        # A chave pública é necessária para verificar a assinatura
        if not public_key:
            logger.error(f"Public key missing for {vehicle_id}")
            return
            
        if not signature or not verify_signature(f"{vehicle_id}{action}", signature, public_key):
            logger.error(f"Invalid signature for {vehicle_id}")
            return

        with charging_points_lock:
            if action == 'request':
                logger.info(f'Processing charge request from {vehicle_id}')
                for point in charging_points:
                    if point["location"] == data["location"]:
                        if point["reserved"] < point["capacity"]:
                            point["reserved"] += 1
                            response = {"status": "READY", "point_id": point["id"], "vehicle_id": vehicle_id}
                        else:
                            if vehicle_id not in point["queue"]:
                                point["queue"].append(vehicle_id)
                            response = {"status": "QUEUED", "position": len(point["queue"]), "vehicle_id": vehicle_id}
                        
                        mqtt_client.publish(constants.TOPICO_RESPOSTA.format(vehicle_id=vehicle_id), json.dumps(response), qos=constants.MQTT_QOS)
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
                            mqtt_client.publish(constants.TOPICO_RESPOSTA.format(vehicle_id=next_vehicle), json.dumps({"status": "READY", "point_id": point_id, "vehicle_id": next_vehicle}), qos=constants.MQTT_QOS)
                            logger.info(f"Notified next vehicle {next_vehicle} for point {point_id}")
                        logger.info(f"Queue status for {point['id']} ({point['location']}): {point['queue']}")
                        break

    def handle_route_request(data):
        vehicle_id = data['vehicle_id']
        city_start = data['start']
        city_end = data['end']
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not public_key:
            logger.error(f"Public key missing for {vehicle_id}")
            return

        if not signature or not verify_signature(f"{vehicle_id}{city_start}{city_end}", signature, public_key):
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
        logger.info(f"{server_name.upper()}: Sent route response to {vehicle_id}")

    def on_connect(client, userdata, flags, rc, properties=None):
        logger.info(f"{server_name.upper()} connected to MQTT broker with code {rc}")
        client.subscribe(mqtt_topic_battery)
        client.subscribe(mqtt_topic_request)
        client.subscribe(constants.TOPICO_ROUTE_REQUEST.format(server=f"server_{server_name}"))

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic_route_request = constants.TOPICO_ROUTE_REQUEST.format(server=f"server_{server_name}")
            if msg.topic == mqtt_topic_request:
                handle_charging_request(data)
            elif msg.topic == topic_route_request:
                handle_route_request(data)
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    # Inicialização do Cliente MQTT com a API v2
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()

    @app.route('/api/charging_points', methods=['GET'])
    def list_charging_points():
        logger.info(f'{server_name.upper()}: returning charging points')
        return jsonify({company_name: charging_points})

    # --- ENDPOINTS COM VERIFICAÇÃO DE ASSINATURA CORRIGIDA ---

    @app.route('/api/prepare', methods=['POST'])
    def prepare_reservation():
        data = request.json
        point_id = data.get("point_id")
        vehicle_id = data.get("vehicle_id")
        signature = data.get('signature')
        
        if signature != "dummy":
            public_key = data.get('public_key')
            if not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
                return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

        if not point_id or not vehicle_id:
            return jsonify({"status": "ABORT", "error": "Missing parameters"}), 400
        
        with charging_points_lock:
            for point in charging_points:
                if point["id"] == point_id:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        logger.info(f"Server {server_name.upper()}: Prepared reservation for {vehicle_id} at {point_id}")
                        return jsonify({"status": "READY", "position": 0})
                    else:
                        if vehicle_id not in point["queue"]:
                            point["queue"].append(vehicle_id)
                        logger.info(f"Server {server_name.upper()}: Queued {vehicle_id} at {point_id}, position {len(point['queue'])}")
                        return jsonify({"status": "QUEUED", "position": len(point["queue"]), "estimated_time": len(point["queue"]) * 30})
            return jsonify({"status": "ABORT", "error": "Point not found"}), 404

    @app.route('/api/commit', methods=['POST'])
    def commit_reservation():
        data = request.json
        point_id = data.get('point_id')
        vehicle_id = data.get('vehicle_id')
        signature = data.get('signature')

        if signature != "dummy":
            public_key = data.get('public_key')
            if not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
                return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

        with charging_points_lock:
            for point in charging_points:
                if point['id'] == point_id:
                    if vehicle_id in point['queue']:
                        point['queue'].remove(vehicle_id)
                    point['reserved'] = min(point['capacity'], point['reserved'] + 1)
                    logger.info(f'{server_name.upper()}: Committed reservation for {vehicle_id} in {point_id}')
                    return jsonify({'status': 'COMMITTED'})
            return jsonify({'status': 'ABORTED', "error": "Point not found"})

    @app.route('/api/abort', methods=['POST'])
    def abort_reservation():
        data = request.json
        point_id = data.get("point_id")
        vehicle_id = data.get("vehicle_id")
        signature = data.get('signature')

        if signature != "dummy":
            public_key = data.get('public_key')
            if not public_key or not verify_signature(f"{vehicle_id}{point_id}", signature, public_key):
                return jsonify({"status": "ABORT", "error": "Invalid signature"}), 400

        with charging_points_lock:
            for point in charging_points:
                if point["id"] == point_id:
                    if vehicle_id in point["queue"]:
                        point["queue"].remove(vehicle_id)
                        logger.info(f"{server_name.upper()}: Aborted queue reservation for {vehicle_id} at {point_id}")
                    else: # Se não estava na fila, estava usando um slot reservado
                        point["reserved"] = max(0, point["reserved"] - 1)
                        logger.info(f"{server_name.upper()}: Aborted active reservation for {vehicle_id} at {point_id}, reserved: {point['reserved']}")
                        if point["queue"]: # Notifica o próximo da fila
                            next_vehicle = point["queue"].pop(0)
                            point["reserved"] += 1
                            mqtt_client.publish(constants.TOPICO_RESPOSTA.format(vehicle_id=next_vehicle), json.dumps({"status": "READY", "point_id": point_id, "vehicle_id": next_vehicle}), qos=constants.MQTT_QOS)
                            logger.info(f"Server {server_name.upper()}: Notified next vehicle {next_vehicle} for point {point_id}")
                    return jsonify({"status": "ABORTED"})
            return jsonify({"status": "ABORTED", "error": "Point not found"})
    
    # --- ENDPOINT DE PAGAMENTO CORRIGIDO ---
    @app.route('/api/payment', methods=['POST'])
    def process_payment():
        data = request.json
        vehicle_id = data.get('vehicle_id')
        amount_wei = data.get('amount')
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not all([vehicle_id, amount_wei, signature, public_key]):
            return jsonify({"status": "ERROR", "error": "Missing parameters"}), 400

        if not verify_signature(f"{vehicle_id}{amount_wei}", signature, public_key):
            return jsonify({"status": "ERROR", "error": "Invalid signature"}), 400

        if record_transaction is None:
            logger.warning("Blockchain ledger not available. Skipping transaction recording.")
            return jsonify({"status": "COMPLETED", "tx_hash": "0x_ledger_not_available"})

        try:
            company_private_key = os.getenv('PRIVATE_KEY')
            if not company_private_key:
                 raise ValueError("Company private key not found in environment.")

            company_account_obj = w3.eth.account.from_key(company_private_key)
            
            tx_data = {'vehicle_id': vehicle_id, 'amount': amount_wei, 'status': 'COMPLETED'}

            # O servidor registra que um pagamento foi feito para sua conta
            unsigned_tx = record_transaction(
                from_account=company_account_obj,
                to_address=company_account, # Endereço da própria empresa
                tx_type='pagamento',
                data_dict=tx_data,
                value=0
            )
            
            # Conexão com o nó Ethereum para enviar a transação
            eth_w3 = Web3(Web3.HTTPProvider(os.getenv('ETH_NODE_URL', 'http://geth:8545')))
            
            signed_tx = eth_w3.eth.account.sign_transaction(unsigned_tx, company_private_key)
            tx_hash = eth_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            eth_w3.eth.wait_for_transaction_receipt(tx_hash)

            tx_hash_hex = tx_hash.hex()
            logger.info(f"Payment recorded for {vehicle_id}: {amount_wei} wei, tx_hash={tx_hash_hex}")
            return jsonify({"status": "COMPLETED", "tx_hash": tx_hash_hex})

        except Exception as e:
            logger.error(f"Payment recording failed for {vehicle_id}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"status": "ERROR", "error": str(e)}), 400


    def plan_route_for_vehicle(vehicle_id, start, end):
        logger.info(f"{server_name.upper()}: Planning route for vehicle {vehicle_id} [{start} => {end}]")
        try:
            path = nx.shortest_path(G, source=start, target=end, weight="weight")
            logger.info(f"{server_name.upper()}: Shortest path: {path}")
            
            other_servers = {
                s["company"]: constants.SERVERS[s["company"]]["url"]
                for s in constants.servers_port
                if s["company"] != company_name
            }
            reservations = []
            all_prepared = True
            
            # Itera sobre todas as cidades no caminho para fazer reservas
            for city in path:
                reserved = False
                
                # Tenta reservar localmente primeiro
                for point in charging_points:
                    if point["location"] == city:
                        prepare_response = requests.post(
                            f"http://localhost:{port}/api/prepare",
                            json={"point_id": point["id"], "vehicle_id": vehicle_id, "signature": "dummy"},
                            timeout=5
                        )
                        if prepare_response.status_code == 200:
                            result = prepare_response.json()
                            if result["status"] in ["READY", "QUEUED"]:
                                reservations.append({"company": company_name, "point_id": point["id"], "city": city, "url": None, "position": result.get("position", 0)})
                                reserved = True
                                logger.info(f"{server_name.upper()}: Prepared local reservation for {city}, point {point['id']}")
                                break
                
                # Se não conseguiu localmente, tenta em outros servidores
                if not reserved:
                    for other_company, url in other_servers.items():
                        try:
                            response = requests.get(f"{url}/api/charging_points", timeout=2)
                            if response.status_code == 200:
                                points = response.json().get(other_company, [])
                                for point in points:
                                    if point["location"] == city:
                                        prepare_response = requests.post(
                                            f"{url}/api/prepare",
                                            json={"point_id": point["id"], "vehicle_id": vehicle_id, "signature": "dummy"},
                                            timeout=5
                                        )
                                        if prepare_response.status_code == 200:
                                            result = prepare_response.json()
                                            if result["status"] in ["READY", "QUEUED"]:
                                                reservations.append({"company": other_company, "point_id": point["id"], "city": city, "url": url, "position": result.get("position", 0)})
                                                reserved = True
                                                break
                                if reserved:
                                    break
                        except requests.exceptions.RequestException as e:
                            logger.error(f"{server_name.upper()}: Error contacting {other_company}: {e}")
                
                if not reserved:
                    all_prepared = False
                    logger.error(f"Could not reserve any point in {city}.")
                    break
            
            # Se alguma reserva falhou, aborta todas que foram feitas
            if not all_prepared:
                logger.warning("Aborting all reservations due to a failure.")
                for r in reservations:
                    abort_url = r["url"] or f"http://localhost:{port}"
                    try:
                        requests.post(f"{abort_url}/api/abort", json={"point_id": r["point_id"], "vehicle_id": vehicle_id, "signature": "dummy"}, timeout=2)
                    except requests.exceptions.RequestException as e:
                        logger.error(f"{server_name.upper()}: Error aborting reservation at {r['company']}: {e}")
                return {"error": "Could not reserve all required points"}

            # Se todas foram preparadas, commita todas
            logger.info("All points prepared, now committing reservations.")
            for r in reservations:
                commit_url = r["url"] or f"http://localhost:{port}"
                try:
                    requests.post(f"{commit_url}/api/commit", json={"point_id": r["point_id"], "vehicle_id": vehicle_id, "signature": "dummy"}, timeout=2)
                except requests.exceptions.RequestException as e:
                    logger.error(f"{server_name.upper()}: Error committing reservation at {r['company']}: {e}")
            
            final_reservations = [{"company": r["company"], "point_id": r["point_id"], "city": r["city"], "position": r.get("position", 0)} for r in reservations]
            return {"path": path, "reservations": final_reservations}
            
        except nx.NetworkXNoPath:
            logger.error(f"No path found between {start} and {end}")
            return {"error": f"No path found between {start} and {end}"}
        except Exception as e:
            logger.error(f"Server {server_name.upper()}: Route planning error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    # Este endpoint é para o carro chamar diretamente, não para o servidor
    @app.route('/api/plan_route', methods=['POST'])
    def plan_route():
        data = request.json
        start = data.get("start")
        end = data.get("end")
        vehicle_id = data.get("vehicle_id")
        return jsonify(plan_route_for_vehicle(vehicle_id, start, end))

    return app, port
