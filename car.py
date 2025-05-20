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

# MQTT topics for battery, reservation request, and response
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"

# Mapping of cities to their server/state
CITY_STATE_MAP = constants.CITY_STATE_MAP

# MQTT broker configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "172.16.201.11")
MQTT_PORT = int(os.getenv("MQTT_PORT", constants.PORTA_MQTT))

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def on_connect(client, userdata, flags, rc):
    """
    Callback when the client connects to the MQTT broker.
    Subscribes to the response topic for this vehicle.
    """
    logger.info(f"Vehicle {userdata['vehicle_id']} connected to MQTT broker with code {rc}")
    client.subscribe(TOPICO_RESPOSTA.format(vehicle_id=userdata['vehicle_id']))

def request_route_planning(client, vehicle_id, start_city, end_city, response_event, response_data):
    """
    Sends a route planning request to the server via MQTT and waits for a response.
    Returns the planned route or an error if timeout occurs.
    """
    server = CITY_STATE_MAP[start_city]['server']
    topic = constants.TOPICO_ROUTE_REQUEST.format(server=server)
    payload = {
        "vehicle_id": vehicle_id,
        "start": start_city,
        "end": end_city
    }
    client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
    logger.info(f"{vehicle_id} requested route planning from {start_city} to {end_city} via MQTT")

    # Wait for response or timeout
    if response_event.wait(timeout=constants.WAITING_TIMEOUT):
        return response_data.get("route_plan")
    else:
        logger.error(f"{vehicle_id} timeout while waiting for route planning response")
        return {"error": "Timeout while waiting for response"}

def on_message(client, userdata, msg):
    """
    Callback when a message is received from MQTT.
    Handles route planning responses and updates userdata accordingly.
    """
    try:
        data = json.loads(msg.payload.decode())
        logger.info(
            f"Vehicle {userdata['vehicle_id']} received message:\n"
            f"  Status: {data.get('status')}\n"
            f"  Route: {data.get('route')}\n"
            f"  Reservations:\n" +
            "\n".join(
            f"    - City: {r.get('city')}, Point: {r.get('point_id')}, Company: {r.get('company')}, Position: {r.get('position')}"
            for r in data.get('reservations', [])
            ) if data.get('reservations') else "  Reservations: None"
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

def simulate_vehicle(vehicle_id, discharge_rate):
    """
    Simulates a vehicle traveling between cities, consuming battery, and recharging at reserved points.
    Handles route planning, battery management, and MQTT communication.
    """
    # Select random start and end cities
    all_cities = list(CITY_STATE_MAP.keys())
    start_city = random.choice(all_cities)
    end_city = random.choice([c for c in all_cities if c != start_city])

    # Userdata for MQTT client and simulation state
    userdata = {
        "vehicle_id": vehicle_id,
        "battery_level": 100.0,
        "current_city": start_city,
        "discharge_rate": discharge_rate,
        "logger": logging.getLogger(f"{vehicle_id}"),
        "response_event": threading.Event(),
        "route_plan": None
    }

    # Initialize MQTT client
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()

        logger.info(f"{vehicle_id} planning route from {start_city} to {end_city}")
        
        # Request route planning
        route_plan = request_route_planning(client, vehicle_id, start_city, end_city, userdata['response_event'], userdata)
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

        # Create a graph of city distances
        G = nx.Graph()
        G.add_edges_from(constants.CITYS_WEIGHT)

        # Travel through the planned route
        while userdata["current_city_index"] < len(route) - 1:
            current_city = route[userdata["current_city_index"]]
            next_city = route[userdata["current_city_index"] + 1]

            # Calculate distance between cities
            distance = G[current_city][next_city]["weight"]

            # Consume battery based on distance and discharge rate
            battery_drain = distance * constants.BATTERY_CONSUMPTION[discharge_rate]
            userdata["battery_level"] = max(0.1, userdata["battery_level"] - battery_drain)

            # Simulate travel time
            time.sleep(distance * constants.TRAVEL_SPEED)

            logger.info(f"{vehicle_id} traveling from {current_city} to {next_city} ({distance} km), battery: {userdata['battery_level']:.2f}%")

            # Update current city
            userdata["current_city_index"] += 1
            userdata["current_city"] = next_city

            # TIRAR AQUI QLQ COISA
            # Consume battery based on distance and discharge rate
            battery_drain = distance * constants.BATTERY_CONSUMPTION[discharge_rate]
            userdata["battery_level"] = max(0.1, userdata["battery_level"] - battery_drain)
            # AQUI 
            logger.info(f"{vehicle_id} arrived at {next_city}, battery: {userdata['battery_level']:.2f}%")

            # Check if recharge is needed at this city
            if next_city in userdata["reservations"]:
                reservation = userdata["reservations"][next_city]
                point_id = reservation["point_id"]
                server = CITY_STATE_MAP[next_city]["server"]



                logger.info(f"{vehicle_id} starting recharge at {next_city} (point {point_id})")
                # Simulate recharging process
                while userdata["battery_level"] < 95:
                    userdata["battery_level"] = min(100, userdata["battery_level"] + 15)
                    logger.info(f"{vehicle_id} recharging at {next_city}, battery: {userdata['battery_level']:.2f}%")
                # Release charging point
                payload = {
                    "vehicle_id": vehicle_id,
                    "point_id": point_id,
                    "action": "done"
                }
                topic = constants.TOPICO_RESERVA.format(server=server)
                client.publish(topic, json.dumps(payload), qos=constants.MQTT_QOS)
                logger.info(f"{vehicle_id} finished recharging at {next_city} and released point {point_id}")

        logger.info(f"{vehicle_id} completed the route at {end_city}, battery: {userdata['battery_level']:.2f}%")

    except Exception as e:
        logger.error(f"Error in vehicle simulation: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    # Get vehicle ID and discharge rate from environment or command line
    vehicle_id = os.getenv("VEHICLE_ID") or sys.argv[1] if len(sys.argv) > 1 else f"vehicle_{random.randint(1,100)}"
    discharge_rate = os.getenv("DISCHARGE_RATE") or sys.argv[2] if len(sys.argv) > 2 else random.choice(["fast", "normal", "slow"])
    
    if discharge_rate not in ["fast", "normal", "slow"]:
        print("Discharge rate must be 'fast', 'normal', or 'slow'")
        sys.exit(1)
    
    simulate_vehicle(vehicle_id, discharge_rate)