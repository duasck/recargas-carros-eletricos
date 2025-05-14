import os
import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import requests
import constants
import networkx as nx

# MQTT setup
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TOPICO_RESPOSTA = constants.TOPICO_RESPOSTA

# Mapeamento de cidades para estados e servidores
CITY_STATE_MAP = {
    "Salvador": {"state": "BA", "server": "server_a"},
    "Feira de Santana": {"state": "BA", "server": "server_a"},
    "Aracaju": {"state": "SE", "server": "server_b"},
    "Itabaiana": {"state": "SE", "server": "server_b"},
    "Maceió": {"state": "AL", "server": "server_c"},
    "Arapiraca": {"state": "AL", "server": "server_c"},
    "Recife": {"state": "PE", "server": "server_d"},
    "Caruaru": {"state": "PE", "server": "server_d"},
    "João Pessoa": {"state": "PB", "server": "server_e"},
    "Campina Grande": {"state": "PB", "server": "server_e"}
}

# Taxas de descarga adicionais (usadas em movimento local)
RATE_RANGES = {
    "fast": (3.0, 6.0),
    "normal": (1.0, 4.0),
    "slow": (0.5, 1.0)
}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    logger.info(f"Car {userdata['vehicle_id']} connected to MQTT broker with code {rc}")
    client.subscribe(TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']))

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Car {userdata['vehicle_id']} received message: {data}")
        if msg.topic == TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']):
            userdata['recharge_status'] = data
            if data.get('status') == 'READY':
                logger.info(f"Vehicle {userdata['vehicle_id']} route planned: {data.get('route')}")
            elif data.get('status') == 'ERROR':
                logger.error(f"Vehicle {userdata['vehicle_id']} route planning failed: {data.get('error')}")
                userdata['recharge_status'] = None
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

def plan_route(vehicle_id, start_city, end_city):
    server = CITY_STATE_MAP[start_city]['server']
    url = constants.SERVERS[f"company_{server[-1]}"]["url"] + "/api/plan_route"
    payload = {
        "vehicle_id": vehicle_id,
        "start": start_city,
        "end": end_city
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to plan route: {response.text}")
            return {"error": "Failed to plan route"}
    except Exception as e:
        logger.error(f"Error planning route: {e}")
        return {"error": str(e)}

def simulate_vehicle(vehicle_id, discharge_rate):
    # Escolher cidades inicial e final aleatoriamente
    all_cities = list(CITY_STATE_MAP.keys())
    start_city = random.choice(all_cities)
    end_city = random.choice([c for c in all_cities if c != start_city])

    # Planejar a rota
    logger.info(f"{vehicle_id} planning route from {start_city} to {end_city}")
    route_plan = plan_route(vehicle_id, start_city, end_city)
    if "error" in route_plan:
        logger.error(f"{vehicle_id} failed to plan route: {route_plan['error']}")
        return

    route = route_plan.get("path", [])
    reservations = route_plan.get("reservations", [])
    if not route or not reservations:
        logger.error(f"{vehicle_id} invalid route or reservations")
        return

    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 100.0,
        "current_city": start_city,
        "recharge_status": {"route": route, "reservations": reservations},
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"{vehicle_id}"),
        "route": route,
        "current_city_index": 0,
        "reservations": {r["city"]: r for r in reservations}
    }

    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        # Simular a viagem
        while userdata["current_city_index"] < len(route) - 1:
            current_city = route[userdata["current_city_index"]]
            next_city = route[userdata["current_city_index"] + 1]

            # Calcular distância (peso da aresta)
            G = nx.Graph()
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
            distance = G[current_city][next_city]["weight"]

            # Consumir bateria com base na distância
            battery_drain = distance * constants.BATTERY_CONSUMPTION[discharge_rate]
            userdata["battery_level"] = max(0.1, userdata["battery_level"] - battery_drain)
            logger.info(f"{vehicle_id} traveling from {current_city} to {next_city} ({distance} km), battery: {userdata['battery_level']:.2f}%")

            # Simular tempo de viagem
            time.sleep(distance * constants.TRAVEL_SPEED)

            # Atualizar cidade atual
            userdata["current_city_index"] += 1
            userdata["current_city"] = next_city
            logger.info(f"{vehicle_id} arrived at {next_city}, battery: {userdata['battery_level']:.2f}%")

            # Verificar se há reserva na cidade atual
            if next_city in userdata["reservations"]:
                reservation = userdata["reservations"][next_city]
                point_id = reservation["point_id"]
                server = CITY_STATE_MAP[next_city]["server"]

                # Simular recarga
                logger.info(f"{vehicle_id} starting charge at {next_city} (point {point_id})")
                while userdata["battery_level"] < 95:
                    userdata["battery_level"] = min(100, userdata["battery_level"] + 15)
                    logger.info(f"{vehicle_id} charging at {next_city}, battery: {userdata['battery_level']:.2f}%")
                    time.sleep(5)  # Simular tempo de recarga por ciclo

                # Liberar o ponto de recarga
                payload = {
                    "vehicle_id": vehicle_id,
                    "point_id": point_id,
                    "action": "done"
                }
                topic = constants.TOPICO_RESERVA.format(server=server)
                client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
                logger.info(f"{vehicle_id} finished charging at {next_city} and released point {point_id}")

            # Pequeno atraso antes de continuar
            time.sleep(5)
            logger.info(f"{vehicle_id} completed route at {end_city}, battery: {userdata['battery_level']:.2f}%")

    except Exception as e:
        logger.error(f"Error in vehicle simulation: {e}")
    finally:
        client.loop_stop()

if __name__ == "__main__":
    vehicle_id = os.getenv("VEHICLE_ID") or sys.argv[1] if len(sys.argv) > 1 else f"vehicle_{random.randint(1,100)}"
    discharge_rate = os.getenv("DISCHARGE_RATE") or sys.argv[2] if len(sys.argv) > 2 else random.choice(["fast", "normal", "slow"])
    
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    
    logger = logging.getLogger(f"{vehicle_id}")
    simulate_vehicle(vehicle_id, discharge_rate)