import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import constants 

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_topic = "vehicle/battery" # mudar esse tópico para particular ao servidor 

# Mapeamento de cidades para estados e servidores
CITY_STATE_MAP = {
    "Salvador": {"state": "BA", "server": "server_a"},
    "Feira de Santana": {"state": "BA", "server": "server_a"},
    "Aracaju": {"state": "SE", "server": "server_b"},
    "Itabaiana": {"state": "SE", "server": "server_b"},
    "Maceió": {"state": "AL", "server": "server_c"},
    "Arapiraca": {"state": "AL", "server": "server_c"}
}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_server_topic(server_name):
    return f"vehicle/{server_name}/battery"

def on_connect(client, userdata, flags, rc):
    logger.info(f"Car {userdata['vehicle_id']} connected to MQTT broker with code {rc}")

def request_recharge(vehicle_id, start_city):
    # Obtém o servidor baseado na cidade de origem
    server_info = CITY_STATE_MAP.get(start_city)
    print(server_info)
    if not server_info:
        logger.error(f"Cidade {start_city} não encontrada no mapeamento")
        return {"error": "Cidade não encontrada"}

    server = server_info["server"]
    cities = list(CITY_STATE_MAP.keys())
    end_city = random.choice([city for city in cities if city != start_city])
    
    payload = {
        "start": start_city,
        "end": end_city,
        "vehicle_id": vehicle_id,
        "state": server_info["state"]
    }

    try:
        logger.info(f"Car {vehicle_id} requesting recharge: {payload}")
        # Publica a mensagem no tópico específico do servidor
        topic = f"recharge/{server}"
        client.publish(topic, json.dumps(payload))
        logger.info(f"Car {vehicle_id} recharge request published to {topic}")
        return payload
    except Exception as e:
        logger.error(f"Car {vehicle_id} failed to request recharge: {e}")
        return {"error": str(e)}

def simulate_vehicle(vehicle_id, discharge_rate):
    #configura a conexão MQTT
    client = mqtt.Client(userdata={"vehicle_id": vehicle_id})
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    battery_level = 30 
    rate_ranges = {"fast": (3.0, 6.0), "normal": (1.0, 4.0), "slow": (0.5, 1.0)}
    min_rate, max_rate = rate_ranges[discharge_rate]
    recharge_requested = False
    current_city = random.choice(list(CITY_STATE_MAP.keys()))

    while True:
        battery_level -= random.uniform(min_rate, max_rate)
        server_topic = get_server_topic(CITY_STATE_MAP[current_city]["server"])
        if battery_level < 0: # ver essa condição aqui dps
            battery_level = 100  # Reset for continuous simulation
            recharge_requested = False
            current_city = random.choice(list(CITY_STATE_MAP.keys()))

        payload = json.dumps({
            "vehicle_id": vehicle_id, 
            "battery_level": round(battery_level, 2),
            "current_city": current_city
        })

        # publicar só no tópico do servidor do carro
        client.publish(server_topic, payload)
        logger.info(f"Car {vehicle_id} published: Battery {round(battery_level, 2)}% in {current_city}")

        # Request recharge if battery <= 20% and not already requested
        if battery_level <= 20 and not recharge_requested:
            request_recharge(vehicle_id, current_city)
            recharge_requested = True  # Prevent multiple requests until reset

        time.sleep(5)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python car.py <vehicle_id> <discharge_rate>")
        sys.exit(1)
    vehicle_id = sys.argv[1]
    discharge_rate = sys.argv[2]
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    simulate_vehicle(vehicle_id, discharge_rate)