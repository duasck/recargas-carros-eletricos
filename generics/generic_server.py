from flask import Flask, request, jsonify
import paho.mqtt.client as mqtt
import json
import requests
import networkx as nx
import logging
import threading
import global_utils.constants as constants

# for run, use "python3 -m generics.generic_server"

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
    G.add_nodes_from(constants.CITYS_NODES)
    G.add_edges_from(constants.CITYS_WEIGHT)

   
    # MQTT config
    mqtt_broker = "172.16.201.11"
    mqtt_port = constants.PORTA_MQTT
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
                    return jsonify({"status": "ABORTED"})
            return jsonify({"status": "ABORTED"})

    # get the queue status from the point
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
                    
    # get the charging status from the all points for the server 
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
        
    # function for plan the route for a vehicle with the start and end city
    def plan_route_for_vehicle(vehicle_id, start, end):
        logger.info(f"{server_name.upper()}: Planning route for vehicle {vehicle_id} [{start} => {end}]")
        try:
            path = nx.shortest_path(G, start, end, weight="weight") # get the shortest way with dijkstra
            logger.info(f"{server_name.upper()}: Shortest path: [{path}]")
            
            # List all servers
            servers = {
                s["company"]: constants.SERVERS[s["company"]]["url"]
                for s in constants.servers_port
                if s["company"] != company_name
            }
            reservations = []
            all_prepared = True
            
            # Fase 1: Prepare
            for i in range(len(path)):
                current_city = path[i]
                reserved = False
                
                # Verify local points first
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
                                json={"point_id": point["id"], "vehicle_id": vehicle_id},
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
                                            json={"point_id": point["id"], "vehicle_id": vehicle_id},
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
            
            # Fase 2: Commit or Abort
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
                                json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
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
                            json={"point_id": r["point_id"], "vehicle_id": vehicle_id},
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

    # endpoint for use the plan route function
    @app.route('/api/plan_route', methods=['POST'])
    def plan_route():
        data = request.json
        start = data.get("start")
        end = data.get("end")
        vehicle_id = data.get("vehicle_id")
        
        if not start or not end or not vehicle_id:
            logger.error(f"Server {server_name.upper()}: Missing start, end, or vehicle_id")
            return jsonify({"error": "Missing start, end, or vehicle_id"}), 400
        
        result = plan_route_for_vehicle(vehicle_id, start, end)
        return jsonify(result)

    return app, port

if __name__ == '__main__':
    print('Working')