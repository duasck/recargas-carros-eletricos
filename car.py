import os
import paho.mqtt.client as mqtt
import json
import random
import time
import logging
import sys
import threading
import networkx as nx
import global_utils.constants as constants
import requests
from ecdsa import SigningKey, SECP256k1
from hashlib import sha256

TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"

CITY_STATE_MAP = constants.CITY_STATE_MAP

MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", constants.PORTA_MQTT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sign_message(message, private_key):
    sk = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1)
    signature = sk.sign(message.encode())
    return signature.hex()

def on_connect(client, userdata, flags, rc, properties=None):
    logger.info(f"Vehicle {userdata['vehicle_id']} connected to MQTT broker with code {rc}")
    client.subscribe(TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']))

def request_route_planning(client, vehicle_id, start_city, end_city, response_event, response_data, private_key, public_key):
    server = CITY_STATE_MAP[start_city]['server']
    topic = constants.TOPICO_ROUTE_REQUEST.format(server=server)
    payload = {
        "vehicle_id": vehicle_id,
        "start": start_city,
        "end": end_city,
        "signature": sign_message(f"{vehicle_id}{start_city}{end_city}", private_key),
        "public_key": public_key
    }
    client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
    logger.info(f"{vehicle_id} requested route planning from {start_city} to {end_city} via MQTT")

    if response_event.wait(timeout=constants.WAITING_TIMEOUT):
        return response_data.get("route_plan")
    else:
        logger.error(f"{vehicle_id} timeout while waiting for route planning response")
        return {"error": "Timeout while waiting for response"}

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        logger.info(
            f"Vehicle {userdata['vehicle_id']} received message:\n"
            f"  Status: {data.get('status')}\n"
            f"  Route: {data.get('route')}\n"
            f"  Reservations:\n" +
            "\n".join(
            f"    - City: {r.get('city')}, Point: {r.get('point_id')}, Company: {r.get('company')}, Position: {r.get('position')}"
            for r in data.get('reservations', [])) if data.get('reservations') else "  Reservations: None"
        )
        if msg.topic == TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']):
            if data.get('status') == 'READY':
                userdata['route_plan'] = data
                userdata['response_event'].set()
            elif data.get('status') == 'ERROR':
                logger.error(f"Route planning failed for vehicle {userdata['vehicle_id']}: {data.get('error')}")
                userdata['route_plan'] = {"error": data.get('error')}
                userdata['response_event'].set()
    except Exception as e:
        logger.error(f"Error processing MQTT message: {e}")

def process_payment(vehicle_id, company, amount_wei, private_key, public_key):
    company_url = constants.SERVERS[company]["url"]
    payload = {
        "vehicle_id": vehicle_id,
        "amount": amount_wei,
        "signature": sign_message(f"{vehicle_id}{amount_wei}", private_key),
        "public_key": public_key
    }
    try:
        response = requests.post(f"{company_url}/api/payment", json=payload, timeout=5)
        result = response.json()
        if result.get("status") == "COMPLETED":
            logger.info(f"{vehicle_id} payment of {amount_wei} wei to {company} completed: {result['tx_hash']}")
            return True
        else:
            logger.error(f"{vehicle_id} payment failed: {result.get('error')}")
            return False
    except Exception as e:
        logger.error(f"{vehicle_id} payment error: {e}")
        return False

def simulate_vehicle(vehicle_id, discharge_rate):
    all_cities = list(CITY_STATE_MAP.keys())
    start_city = random.choice(all_cities)
    end_city = random.choice([c for c in all_cities if c != start_city])

    private_key = os.getenv("VEHICLE_PRIVATE_KEY", SigningKey.generate(curve=SECP256k1).to_string().hex())
    public_key = SigningKey.from_string(bytes.fromhex(private_key), curve=SECP256k1).verifying_key.to_string().hex()

    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 100.0,
        "current_city": start_city,
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"{vehicle_id}"),
        "response_event": threading.Event(),
        "route_plan": None,
        "private_key": private_key,
        "public_key": public_key
    }

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        logger.info(f"{vehicle_id} planning route from {start_city} to {end_city}")
        
        route_plan = request_route_planning(client, vehicle_id, start_city, end_city, userdata['response_event'], userdata, private_key, public_key)
        if "error" in route_plan:
            logger.error(f"{vehicle_id} failed to plan route: {route_plan['error']}")
            return

        route = route_plan.get("route", [])
        reservations = route_plan.get("reservations", [])
        if not route or not reservations:
            logger.error(f"{vehicle_id} invalid route or reservations")
            return

        userdata["route"] = route
        userdata["current_city_index"] = 0
        userdata["reservations"] = {r["city"]: r for r in reservations}

        G = nx.Graph()
        G.add_edges_from(constants.CITYS_WEIGHT)

        while userdata["current_city_index"] < len(route) - 1:
            current_city = route[userdata["current_city_index"]]
            next_city = route[userdata["current_city_index"] + 1]

            distance = G[current_city][next_city]["weight"]
            battery_drain = distance * constants.BATTERY_CONSUMPTION[discharge_rate]
            userdata["battery_level"] = max(0.1, userdata["battery_level"] - battery_drain)

            time.sleep(distance * constants.TRAVEL_SPEED)

            logger.info(f"{vehicle_id} traveling from {current_city} to {next_city} ({distance} km), battery: {userdata['battery_level']:.2f}%")

            userdata["current_city_index"] += 1
            userdata["current_city"] = next_city

            logger.info(f"{vehicle_id} arrived at {next_city}, battery: {userdata['battery_level']:.2f}%")

            if next_city in userdata["reservations"]:
                reservation = userdata["reservations"][next_city]
                point_id = reservation["point_id"]
                company = reservation["company"]
                server = CITY_STATE_MAP[next_city]["server"]

                logger.info(f"{vehicle_id} starting recharge at {next_city} (point {point_id})")
                charge_amount = 0
                while userdata["battery_level"] < 95:
                    userdata["battery_level"] = min(100, userdata["battery_level"] + 15)
                    charge_amount += 15
                    logger.info(f"{vehicle_id} recharging at {next_city}, battery: {userdata['battery_level']:.2f}%")
                    time.sleep(1)

                payload = {
                    "vehicle_id": vehicle_id,
                    "point_id": point_id,
                    "action": "done",
                    "signature": sign_message(f"{vehicle_id}done", private_key),
                    "public_key": public_key
                }
                topic = constants.TOPICO_RESERVA.format(server=server)
                client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
                logger.info(f"{vehicle_id} finished recharging at {next_city} and released point {point_id}")

                # Processar pagamento
                cost_wei = int(charge_amount * 1e15)  # 1% de bateria = 1e15 wei
                if process_payment(vehicle_id, company, cost_wei, private_key, public_key):
                    logger.info(f"{vehicle_id} paid {cost_wei} wei for recharge at {next_city}")
                else:
                    logger.error(f"{vehicle_id} failed to pay for recharge at {next_city}")
                    return

        logger.info(f"{vehicle_id} completed the route at {end_city}, battery: {userdata['battery_level']:.2f}%")

    except Exception as e:
        logger.error(f"Error in vehicle simulation: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    vehicle_id = os.getenv("VEHICLE_ID") or sys.argv[1] if len(sys.argv) > 1 else f"vehicle_{random.randint(1,100)}"
    discharge_rate = os.getenv("DISCHARGE_RATE") or sys.argv[2] if len(sys.argv) > 2 else random.choice(["fast", "normal", "slow"])
    
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    
    simulate_vehicle(vehicle_id, discharge_rate)
