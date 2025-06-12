from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import global_utils.constants as constants
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

    mqtt_broker = os.getenv("MQTT_BROKER", "mosquitto")
    mqtt_port = constants.PORTA_MQTT

    mqtt_topic_request = constants.TOPICO_RESERVA.format(server=f"server_{server_name}")
    mqtt_topic_battery = constants.TOPICO_BATERIA.format(server=f"server_{server_name}")

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
                tx_hash = registrar_transacao('recarga', {'vehicle_id': vehicle_id, 'action': action, 'status': 'INICIO'}, vehicle_id, company_account)
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
        logger.info(f"{server_name.upper()}: Sent route response to {vehicle_id}")

    def on_connect(client, userdata, flags, rc):
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

    mqtt_client = mqtt.Client()
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
                                tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'PREPARE'}, vehicle_id, company_account)
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
                            tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'COMMIT'}, vehicle_id, company_account)
                            logger.info(f'Transação blockchain registrada: tipo=reserva, dados={{"point_id": "{point_id}", "vehicle_id": "{vehicle_id}", "status": "COMMIT"}}, tx_hash={tx_hash}')
                        except Exception as e:
                            logger.warning(f'Erro ao registrar no blockchain: {e}')
                    return jsonify({'status': 'COMMITTED'})
            return jsonify({'status': 'ABORTED'})

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
                            tx_hash = registrar_transacao('reserva', {'point_id': point_id, 'vehicle_id': vehicle_id, 'status': 'ABORT'}, vehicle_id, company_account)
                            logger.info(f'Transação blockchain registrada: tipo=reserva, dados={{"point_id": "{point_id}", "vehicle_id": "{vehicle_id}", "status": "ABORT"}}, tx_hash={tx_hash}')
                        except Exception as e:
                            logger.warning(f'Erro ao registrar no blockchain: {e}')
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

    @app.route('/api/payment', methods=['POST'])
    def process_payment():
        # (A lógica de verificação de assinatura e parâmetros permanece a mesma)
        data = request.json
        vehicle_id = data.get('vehicle_id')
        amount_wei = data.get('amount')
        signature = data.get('signature')
        public_key = data.get('public_key')

        if not vehicle_id or not amount_wei or not signature or not public_key:
            return jsonify({"status": "ERROR", "error": "Missing parameters"}), 400

        if not verify_signature(f"{vehicle_id}{amount_wei}", signature, public_key):
            return jsonify({"status": "ERROR", "error": "Invalid signature"}), 400
        
        # --- LÓGICA DE TRANSAÇÃO CORRIGIDA ---
        try:
            # Precisamos da conta do veículo para iniciar a transação.
            # No mundo real, o veículo assinaria a transação e a enviaria para o servidor apenas para retransmissão.
            # Aqui, vamos simular isso. O servidor não deveria ter a chave privada do veículo.
            # PORÉM, para simplificar o projeto e fazer funcionar, vamos assumir que o servidor
            # pode iniciar a transação em nome do sistema, registrando o pagamento.
            # O ideal seria que a função de pagamento fosse chamada pelo carro.
            
            # Buscando a conta da empresa para ser o 'from' da transação de registro.
            # O pagamento real (transferência de valor) já foi feito pelo carro.
            # Esta é apenas uma transação de registro.
            
            # Vamos precisar de uma conta para o servidor/empresa
            # Supondo que a chave privada da empresa está disponível via variável de ambiente
            company_private_key = os.getenv('PRIVATE_KEY')
            if not company_private_key:
                 raise ValueError("Chave privada da empresa não encontrada no ambiente.")

            company_account_obj = w3.eth.account.from_key(company_private_key)
            vehicle_eth_address = "0x" + "0" * 40 # Placeholder, idealmente viria do `keys.json`

            # Encontrar o endereço do veículo a partir do seu ID
            try:
                with open("keys.json", "r") as f:
                    keys = json.load(f)
                for v in keys['vehicles']:
                    if v['id'] == vehicle_id:
                        vehicle_eth_address = v['address']
                        break
            except Exception:
                logger.warning(f"Não foi possível encontrar o endereço Ethereum para {vehicle_id}")


            # Construindo a transação de registro do pagamento
            tx_data = {'vehicle_id': vehicle_id, 'amount': amount_wei, 'status': 'COMPLETED'}

            # A transação que transfere valor deve ser iniciada pelo veículo.
            # A transação que o servidor faz é apenas para registrar o evento.
            # Vamos assumir que a chamada à API de pagamento é a confirmação e o servidor registra.
            # O 'to' aqui é a própria empresa, registrando um pagamento recebido.
            unsigned_tx = record_transaction(
                from_account=company_account_obj,
                to_address=company_account, # Endereço da empresa
                tx_type='pagamento',
                data_dict=tx_data,
                value=0 # Apenas registro, sem transferência de valor
            )
            
            signed_tx = w3.eth.account.sign_transaction(unsigned_tx, company_private_key)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)

            tx_hash_hex = tx_hash.hex()
            logger.info(f"Payment processed and recorded for {vehicle_id}: {amount_wei} wei, tx_hash={tx_hash_hex}")
            return jsonify({"status": "COMPLETED", "tx_hash": tx_hash_hex})

        except Exception as e:
            logger.error(f"Payment failed for {vehicle_id}: {e}")
            # Adiciona o traceback ao log para facilitar a depuração
            import traceback
            traceback.print_exc()
            return jsonify({"status": "ERROR", "error": str(e)}), 400

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
