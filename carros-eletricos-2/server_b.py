from flask import Flask, jsonify
import paho.mqtt.client as mqtt
import json
import logging
import threading
import networkx as nx

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    vehicle_id = data['vehicle_id']
    action = data.get('action')
    
    if action == "request":
        for point in charging_points:
            if point['reserved'] < point['capacity']:
                point['reserved'] += 1
                response = {
                    'status': 'READY',
                    'point_id': point['id'],
                    'vehicle_id': vehicle_id
                }
                break
            else:
                point['queue'].append(vehicle_id)
                response = {
                    'status': 'QUEUED',
                    'position': len(point['queue']),
                    'vehicle_id': vehicle_id
                }
        
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps(response)
        )
        logger.info(f"Sent response to {vehicle_id}: {response}")
    
    elif action == "done":
        for point in charging_points:
            if point['id'] == data['point_id']:
                point['reserved'] = max(0, point['reserved'] - 1)
                if point['queue']:
                    next_vehicle = point['queue'].pop(0)
                    point['reserved'] += 1
                    mqtt_client.publish(
                        f"charging/{next_vehicle}/response",
                        json.dumps({
                            'status': 'READY',
                            'point_id': point['id'],
                            'vehicle_id': next_vehicle
                        })
                    )
                break

def handle_low_battery(vehicle_id, current_city):
    try:
        logger.info(f"Server B planning route for {vehicle_id} from {current_city}")
        end_city = "Maceió"  # Destino padrão diferente se necessário
        
        # Diferente: Prioriza pontos de Sergipe
        path = nx.shortest_path(G, current_city, end_city, weight="weight")
        
        for city in path[:-1]:  # Exclui o destino final
            # Diferente: Verifica apenas pontos de Sergipe (SE1, SE2)
            for point in charging_points:
                if point["location"] == city:
                    if point["reserved"] < point["capacity"]:
                        point["reserved"] += 1
                        response = {
                            "status": "READY",
                            "point_id": point["id"],
                            "city": city,
                            "server": "b"  # Diferente: Identifica o servidor
                        }
                        break
                    else:
                        point["queue"].append(vehicle_id)
                        response = {
                            "status": "QUEUED",
                            "position": len(point["queue"]),
                            "city": city,
                            "server": "b"
                        }
                        break
            
            mqtt_client.publish(
                f"charging/{vehicle_id}/response",
                json.dumps(response)
            )

    except Exception as e:
        logger.error(f"Server B route error: {e}")
        mqtt_client.publish(
            f"charging/{vehicle_id}/response",
            json.dumps({
                "status": "ERROR",
                "error": str(e),
                "server": "b"
            })
        )

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

if __name__ == '__main__':
    # Configura MQTT
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect(mqtt_broker, mqtt_port, 60)
    mqtt_client.loop_start()
    
    # Inicia servidor Flask
    app.run(host='0.0.0.0', port=5001)