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
    "fast": (3.0, 6.0),   # Descarga rápida
    "normal": (1.0, 4.0), # Descarga normal
    "slow": (0.5, 1.0)    # Descarga lenta
}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        return
    
    payload = {
        "vehicle_id": vehicle_id,
        "location": current_city,
        "battery_level": client._userdata['battery_level'],
        "action": "request"
    }
    
    topic = TOPICO_RESERVA.format(server=server_info['server'])
    client.publish(topic, json.dumps(payload))
    logger.info(f"Vehicle {vehicle_id} sent recharge request to {topic}")


"""
def request_recharge(vehicle_id, start_city):
    server_info = CITY_STATE_MAP.get(start_city)
    if not server_info:
        return {"error": "Cidade não encontrada"}

    server = server_info["server"]
    url = f"http://{server}:{constants.PORT_BASE + ['a','b','c'].index(server[-1])}"
    
    try:
        # 1. Verifica pontos disponíveis
        points_response = requests.get(f"{url}/api/charging_points")
        points = points_response.json().get(f"company_{server[-1]}", [])
        
        # 2. Tenta reservar em cada ponto (ordem de preferência)
        for point in points:
            prepare_response = requests.post(
                f"{url}/api/prepare",
                json={"point_id": point["id"], "vehicle_id": vehicle_id},
                timeout=2
            )
            
            if prepare_response.status_code == 200:
                result = prepare_response.json()
                if result["status"] == "READY":
                    return {
                        "status": "RESERVED",
                        "point_id": point["id"],
                        "position": 0
                    }
                elif result["status"] == "QUEUED":
                    return {
                        "status": "IN_QUEUE",
                        "point_id": point["id"],
                        "position": result["position"],
                        "estimated_time": result["estimated_time"]
                    }
        
        return {"error": "No available charging points"}
    except Exception as e:
        return {"error": str(e)}
"""
def simulate_vehicle(vehicle_id, discharge_rate):
    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 30,
        "current_city": random.choice(list(CITY_STATE_MAP.keys())),
        "recharge_status": None,
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"Vehicle_{vehicle_id}")
    }
    
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        while True:
            # 1. Atualiza nível da bateria
            userdata['battery_level'] -= random.uniform(*RATE_RANGES[discharge_rate])
            userdata['battery_level'] = max(0, userdata['battery_level'])

            # 2. Publica estado da bateria
            server_topic = TOPICO_BATERIA.format(server=CITY_STATE_MAP[userdata['current_city']]['server'])
            client.publish(server_topic, json.dumps({
                "vehicle_id": vehicle_id,
                "battery_level": round(userdata['battery_level'], 2),
                "current_city": userdata['current_city']
            }))
            logger.info(f"Vehicle {vehicle_id} battery: {userdata['battery_level']:.2f}%")

            # 3. Lógica de recarga
            if userdata['battery_level'] <= 20 and not userdata['recharge_status']:
                request_recharge(client, vehicle_id, userdata['current_city'])
            
            # 4. Se está na fila
            elif userdata['recharge_status'] and userdata['recharge_status'].get('status') == 'QUEUED':
                userdata['battery_level'] -= 0.2  # Descarga mínima enquanto espera
                logger.info(f"Vehicle {vehicle_id} in queue (position {userdata['recharge_status'].get('position')})")
            
            # 5. Se está carregando
            elif userdata['recharge_status'] and userdata['recharge_status'].get('status') == 'READY':
                userdata['battery_level'] = min(100, userdata['battery_level'] + 15)  # Carrega 15% por ciclo
                
                if userdata['battery_level'] >= 95:
                    # Notifica término
                    payload = {
                        "vehicle_id": vehicle_id,
                        "point_id": userdata['recharge_status']['point_id'],
                        "action": "done"
                    }
                    topic = TOPICO_RESERVA.format(server=CITY_STATE_MAP[userdata['current_city']]['server'])
                    client.publish(topic, json.dumps(payload))
                    userdata['recharge_status'] = None
                    userdata['current_city'] = random.choice(list(CITY_STATE_MAP.keys()))
                    logger.info(f"Vehicle {vehicle_id} finished charging, moving to {userdata['current_city']}")

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
    logger = logging.getLogger(f"Vehicle_{vehicle_id}")
    
    simulate_vehicle(vehicle_id, discharge_rate)