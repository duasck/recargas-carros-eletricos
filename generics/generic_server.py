from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
from global_utils import constants 

def create_server(server_config):
    # server's configs
    company_name = server_config['company']
    server_name = server_config['name']
    port = server_config['port']
    charging_points = server_config['charging_points']

    # Global Lock for the charging points, for the race conditions
    charging_points_lock = threading.Lock()

    app = Flask(__name__)

    # logging configs
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(f'Server_{server_name.upper()}')
    
    # a graph for the router plan 
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

    # MQTT config
    mqtt_broker = "broker.hivemq.com"
    mqtt_port = 1883
    mqtt_topic_battery = constants.TOPICO_BATERIA.format(server=f"server_{server_name}")
    mqtt_topic_request = constants.TOPICO_RESERVA.format(server=f"server_{server_name}")

    def handle_charging_request(data):

        vehicle_id = data['vehicle_id']
        action = data['action']

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

    def handle_route_request(data):
        vehicle_id = data['vehicle_id']
        city_start = data['start']
        city_end = data['end']

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
        client.subscribe(constants.TOPICO_ROUTE_REQUEST.format(server=f"{server_name}"))

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

    # list all points from the server
    @app.route('/api/charging_points', methods=['GET'])
    def list_charging_points():
        logger.info(f'{server_name.upper()}: returning charging points')
        return jsonify({company_name: charging_points})

    # prepare phase from the 2pc
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
                        logger.info(f"Server {server_name.upper()}: Prepared reservation for {vehicle_id} at {point_id}")
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

        with charging_points_lock:
            for point in charging_points:
                if point['id'] == point_id:
                    if vehicle_id in point['queue']:
                        point['queue'].remove(vehicle_id)
                        point['reserved'] += 1
                    logger.info(f'{server_name.upper()}: Commited reservation for {vehicle_id} in {point_id}')
                    return jsonify({'status': 'COMMITED'})
            return jsonify({'status': 'ABORTED'})
                    
if __name__ == '__main__':
    print('Working')