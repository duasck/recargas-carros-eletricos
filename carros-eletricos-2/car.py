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

def simulate_vehicle(vehicle_id, discharge_rate):
    client = mqtt.Client(userdata={"vehicle_id": vehicle_id})
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()

    battery_level = 30 
    current_city = random.choice(list(CITY_STATE_MAP.keys()))
    recharge_status = None
    server_topic = get_server_topic(CITY_STATE_MAP[current_city]["server"])

    while True:
        # Atualiza nível da bateria
        discharge_rate_range = RATE_RANGES.get(discharge_rate, (1.0, 3.0))  # Default se não encontrado
        battery_level -= random.uniform(*discharge_rate_range)
        battery_level = max(0, battery_level)  # Não deixa ficar negativo

        # Publica status
        client.publish(
            server_topic,
            json.dumps({
                "vehicle_id": vehicle_id,
                "battery_level": round(battery_level, 2),
                "current_city": current_city,
                "recharge_status": recharge_status
            })
        )

        # Lógica de recarga
        if battery_level <= 20 and not recharge_status:
            recharge_status = request_recharge(vehicle_id, current_city)
            if "error" in recharge_status:
                logger.error(f"Vehicle {vehicle_id} recharge failed: {recharge_status['error']}")
                recharge_status = None
        
        # Se está na fila, verifica progresso
        elif recharge_status and recharge_status.get("status") == "IN_QUEUE":
            try:
                check_response = requests.get(
                    f"http://{CITY_STATE_MAP[current_city]['server']}:{constants.PORT_BASE + ['a','b','c'].index(CITY_STATE_MAP[current_city]['server'][-1])}/api/queue_status/{recharge_status['point_id']}",
                    timeout=2
                )
                if check_response.status_code == 200:
                    queue_info = check_response.json()
                    if queue_info["reserved"] < queue_info.get("capacity", 1):
                        recharge_status["position"] = max(0, recharge_status["position"] - 1)
                        if recharge_status["position"] <= 0:
                            recharge_status["status"] = "READY"
            except Exception as e:
                logger.error(f"Vehicle {vehicle_id} queue check error: {e}")

        # Se está carregando
        elif recharge_status and recharge_status.get("status") == "READY":
            battery_level = min(100, battery_level + 15)  # Carrega 15% por ciclo
            if battery_level >= 95:
                try:
                    requests.post(
                        f"http://{CITY_STATE_MAP[current_city]['server']}:{constants.PORT_BASE + ['a','b','c'].index(CITY_STATE_MAP[current_city]['server'][-1])}/api/abort",
                        json={"point_id": recharge_status["point_id"], "vehicle_id": vehicle_id},
                        timeout=2
                    )
                    recharge_status = None
                    current_city = random.choice(list(CITY_STATE_MAP.keys()))
                    server_topic = get_server_topic(CITY_STATE_MAP[current_city]["server"])
                except Exception as e:
                    logger.error(f"Vehicle {vehicle_id} abort error: {e}")

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
    
    #configura a conexão MQTT
    client = mqtt.Client(userdata={"vehicle_id": vehicle_id})
    client.on_connect = on_connect
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_start()
    simulate_vehicle(vehicle_id, discharge_rate)