import os
import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import constants 

# MQTT setup
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"

# Mapeamento de cidades para estados e servidores
CITY_STATE_MAP = {
    "Salvador": {"state": "BA", "server": "server_a"},
    "Feira de Santana": {"state": "BA", "server": "server_a"},
    "Aracaju": {"state": "SE", "server": "server_b"},
    "Itabaiana": {"state": "SE", "server": "server_b"},
    "Maceió": {"state": "AL", "server": "server_c"},
    "Arapiraca": {"state": "AL", "server": "server_c"}
}

# Taxas de descarga (min, max) por tipo
RATE_RANGES = {
    "fast": (3.0, 6.0),   
    "normal": (1.0, 4.0), 
    "slow": (0.5, 1.0)    
}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_server_topic(server_name):
    return f"vehicle/{server_name}/battery"

def on_connect(client, userdata, flags, rc):
    logger.info(f"Car {userdata['vehicle_id']} connected to MQTT broker with code {rc}")
    # Subscreve ao tópico de respostas específico para este veículo
    client.subscribe(TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']))

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Car {userdata['vehicle_id']} received message: {data}")
        
        if msg.topic == TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']):
            userdata['recharge_status'] = data
            if data.get('status') == 'QUEUED':
                logger.info(f"Vehicle {userdata['vehicle_id']} is in queue, position {data.get('position')}")
            elif data.get('status') == 'READY':
                logger.info(f"Vehicle {userdata['vehicle_id']} can now charge at {data.get('point_id')}")
                
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

def request_recharge(client, vehicle_id, current_city):
    server_info = CITY_STATE_MAP.get(current_city)
    if not server_info:
        logger.error(f"No server found for city {current_city}")
        return
    
    payload = {
        "vehicle_id": vehicle_id,
        "location": current_city,
        "battery_level": client._userdata['battery_level'],
        "action": "request"
    }
    
    topic = TOPICO_RESERVA.format(server=server_info['server'])
    client.publish(topic, json.dumps(payload), qos=1)  # QoS=1 para entrega garantida
    logger.info(f"{vehicle_id} sent recharge request to {topic}")


def simulate_vehicle(vehicle_id, discharge_rate):
    # Definir uma rota predefinida
    all_cities = list(CITY_STATE_MAP.keys())
    route = random.sample(all_cities, len(all_cities))  # Rota aleatória
    current_city_index = 0
    current_city = route[current_city_index]
    
    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 40,
        "current_city": current_city,
        "recharge_status": None,
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"{vehicle_id}"),
        "route": route,
        "current_city_index": current_city_index,
        "has_requested_recharge": False,
        "is_waiting": False
    }
    
    logger.info(f"{vehicle_id} route: {route}")

    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        while True:
            # Atualizar bateria
            if not userdata['is_waiting'] and not (userdata['recharge_status'] and userdata['recharge_status'].get('status') == 'READY'):
                drain = random.uniform(*RATE_RANGES[discharge_rate])
                userdata['battery_level'] = max(0.1, userdata['battery_level'] - drain)
            
            # Lógica de recarga
            if (userdata['battery_level'] <= 20 and 
                not userdata['recharge_status'] and 
                not userdata['has_requested_recharge']):
                request_recharge(client, vehicle_id, userdata['current_city'])
                userdata['has_requested_recharge'] = True
                userdata['is_waiting'] = True
                logger.info(f"{vehicle_id} requested recharge at {userdata['current_city']}")
            
            # Comportamento enquanto espera ou carrega
            elif userdata['is_waiting'] or (userdata['recharge_status'] and userdata['recharge_status'].get('status') in ['QUEUED', 'READY']):
                behavior = random.choice(['stationary', 'moving'])
                if behavior == 'stationary':
                    logger.info(f"{vehicle_id} is stationary at {userdata['current_city']}")
                else:
                    drain = random.uniform(0.1, 0.3)
                    userdata['battery_level'] = max(0.1, userdata['battery_level'] - drain)
                    logger.info(f"{vehicle_id} is moving near {userdata['current_city']}, battery at {userdata['battery_level']:.2f}%")
            
            # Atualizar posição na rota
            if not userdata['is_waiting'] and not userdata['recharge_status']:
                # Avançar para a próxima cidade após um tempo
                if random.random() < 0.1:  # 10% de chance de mudar de cidade por ciclo
                    userdata['current_city_index'] = (userdata['current_city_index'] + 1) % len(route)
                    userdata['current_city'] = route[userdata['current_city_index']]
                    logger.info(f"{vehicle_id} moved to {userdata['current_city']}")
            
            # Lógica de carregamento
            if userdata['recharge_status'] and userdata['recharge_status'].get('status') == 'READY':
                userdata['battery_level'] = min(100, userdata['battery_level'] + 15)
                logger.info(f"{vehicle_id} charging at {userdata['current_city']}, battery: {userdata['battery_level']:.2f}%")
                
                if userdata['battery_level'] >= 95:
                    payload = {
                        "vehicle_id": vehicle_id,
                        "point_id": userdata['recharge_status']['point_id'],
                        "action": "done"
                    }
                    topic = TOPICO_RESERVA.format(server=CITY_STATE_MAP[userdata['current_city']]['server'])
                    client.publish(topic, json.dumps(payload), qos=1)
                    logger.info(f"{vehicle_id} finished charging at {userdata['current_city']}")
                    userdata['recharge_status'] = None
                    userdata['has_requested_recharge'] = False
                    userdata['is_waiting'] = False
            
            time.sleep(5)
            
    except Exception as e:
        logger.error(f"Error in vehicle simulation: {e}")
    finally:
        client.loop_stop()
        

if __name__ == "__main__":
    # Obtém variáveis de ambiente ou argumentos
    vehicle_id = os.getenv("VEHICLE_ID") or sys.argv[1] if len(sys.argv) > 1 else f"vehicle_{random.randint(1,100)}"
    discharge_rate = os.getenv("DISCHARGE_RATE") or sys.argv[2] if len(sys.argv) > 2 else random.choice(["fast", "normal", "slow"])
    
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(f"{vehicle_id}")
    
    simulate_vehicle(vehicle_id, discharge_rate)