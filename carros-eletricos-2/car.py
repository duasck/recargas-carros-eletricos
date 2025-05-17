import os
import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import threading
import networkx as nx
import constants

# Configuração do MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
TOPICO_RESPOSTA = constants.TOPICO_RESPOSTA  # "charging/{vehicle_id}/response"

# Mapeamento de cidades para estados e servidores
CITY_STATE_MAP = constants.CITY_STATE_MAP

# Taxas de consumo de bateria
BATTERY_CONSUMPTION = {
    "fast": 1,  # 10% por 100 km
    "normal": 0.5,  # 5% por 100 km
    "slow": 0.25  # 2.5% por 100 km
}

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    logger.info(f"Carro {userdata['vehicle_id']} conectado ao broker MQTT com código {rc}")
    client.subscribe(TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']))

def request_route_planning(client, vehicle_id, start_city, end_city, response_event, response_data):
    server = CITY_STATE_MAP[start_city]['server']
    topic = constants.TOPICO_ROUTE_REQUEST.format(server=server)
    payload = {
        "vehicle_id": vehicle_id,
        "start": start_city,
        "end": end_city
    }
    client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
    logger.info(f"{vehicle_id} solicitou planejamento de rota de {start_city} para {end_city} via MQTT")

    if response_event.wait(timeout=constants.WAITING_TIMEOUT):
        return response_data.get("route_plan")
    else:
        logger.error(f"{vehicle_id} timeout ao esperar resposta do planejamento de rota")
        return {"error": "Timeout ao esperar resposta"}

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        logger.info(f"Carro {userdata['vehicle_id']} recebeu mensagem: {data}")
        if msg.topic == TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']):
            if data.get('status') == 'READY':
                userdata['route_plan'] = data
                userdata['response_event'].set()
            elif data.get('status') == 'ERROR':
                logger.error(f"Falha no planejamento de rota do veículo {userdata['vehicle_id']}: {data.get('error')}")
                userdata['route_plan'] = {"error": data.get('error')}
                userdata['response_event'].set()
    except Exception as e:
        logger.error(f"Erro ao processar mensagem MQTT: {e}")

def simulate_vehicle(vehicle_id, discharge_rate):
    all_cities = list(CITY_STATE_MAP.keys())
    start_city = random.choice(all_cities)
    end_city = random.choice([c for c in all_cities if c != start_city])

    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 100.0,
        "current_city": start_city,
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"{vehicle_id}"),
        "response_event": threading.Event(),
        "route_plan": None
    }

    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        logger.info(f"{vehicle_id} planejando rota de {start_city} para {end_city}")
        route_plan = request_route_planning(client, vehicle_id, start_city, end_city, userdata['response_event'], userdata)
        if "error" in route_plan:
            logger.error(f"{vehicle_id} falhou ao planejar rota: {route_plan['error']}")
            return

        route = route_plan.get("route", [])
        reservations = route_plan.get("reservations", [])
        if not route or not reservations:
            logger.error(f"{vehicle_id} rota ou reservas inválidas")
            return

        userdata["route"] = route
        userdata["current_city_index"] = 0
        userdata["reservations"] = {r["city"]: r for r in reservations}

        # Grafo de distâncias entre cidades
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

        while userdata["current_city_index"] < len(route) - 1:
            current_city = route[userdata["current_city_index"]]
            next_city = route[userdata["current_city_index"] + 1]

            # Calcular distância
            distance = G[current_city][next_city]["weight"]

            # Consumir bateria
            battery_drain = distance * BATTERY_CONSUMPTION[discharge_rate]
            userdata["battery_level"] = max(0.1, userdata["battery_level"] - battery_drain)
            logger.info(f"{vehicle_id} viajando de {current_city} para {next_city} ({distance} km), bateria: {userdata['battery_level']:.2f}%")

            # Simular tempo de viagem
            time.sleep(distance * constants.TRAVEL_SPEED)

            # Atualizar cidade atual
            userdata["current_city_index"] += 1
            userdata["current_city"] = next_city
            logger.info(f"{vehicle_id} chegou em {next_city}, bateria: {userdata['battery_level']:.2f}%")

            # Verificar recarga
            if next_city in userdata["reservations"]:
                reservation = userdata["reservations"][next_city]
                point_id = reservation["point_id"]
                server = CITY_STATE_MAP[next_city]["server"]

                logger.info(f"{vehicle_id} iniciando recarga em {next_city} (ponto {point_id})")
                while userdata["battery_level"] < 95:
                    userdata["battery_level"] = min(100, userdata["battery_level"] + 15)
                    logger.info(f"{vehicle_id} recarregando em {next_city}, bateria: {userdata['battery_level']:.2f}%")
                    time.sleep(5)  # Simular tempo de recarga

                # Liberar ponto de recarga
                payload = {
                    "vehicle_id": vehicle_id,
                    "point_id": point_id,
                    "action": "done"
                }
                topic = constants.TOPICO_RESERVA.format(server=server)
                client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
                logger.info(f"{vehicle_id} terminou recarga em {next_city} e liberou ponto {point_id}")

            time.sleep(5)  # Pausa antes de continuar
        logger.info(f"{vehicle_id} completou a rota em {end_city}, bateria: {userdata['battery_level']:.2f}%")

    except Exception as e:
        logger.error(f"Erro na simulação do veículo: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    vehicle_id = os.getenv("VEHICLE_ID") or sys.argv[1] if len(sys.argv) > 1 else f"vehicle_{random.randint(1,100)}"
    discharge_rate = os.getenv("DISCHARGE_RATE") or sys.argv[2] if len(sys.argv) > 2 else random.choice(["fast", "normal", "slow"])
    
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Taxa de descarga deve ser 'fast', 'normal' ou 'slow'")
        sys.exit(1)
    
    simulate_vehicle(vehicle_id, discharge_rate)
