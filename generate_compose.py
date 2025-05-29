import sys
import os
import yaml
import global_utils.constants as CONST
import random

DEFAULT_NUM_CARS = 5

def generate_servers_compose(servers_port):
    services = {}
    for s in servers_port:
        company = s["name"].lower()
        port = s["port"]
        services[f"server_{company}"] = {
            "build": {"context": "."},
            "command": f"python servers/server_{company}.py",
            "container_name": f"server_{company}",
            "ports": [f"{port}:{port}"],
            "networks": ["carros_net"]
        }
    # Adiciona o serviço do nó Ethereum (geth) para blockchain
    services["geth"] = {
        "image": "ethereum/client-go",
        "container_name": "geth",
        "ports": [
            "8545:8545",
            "30303:30303"
        ],
        "command": "--dev --http --http.addr 0.0.0.0 --http.api eth,net,web3,personal --http.corsdomain=* --http.vhosts=*",
        "networks": ["carros_net"]
    }
    services["mosquitto"] = {
        "image": "eclipse-mosquitto",
        "container_name": "mosquitto",
        "ports": [
            "18833:18833",
            "9001:9001"
        ],
        "volumes": [
            "./mosquitto/config:/mosquitto/config",
            "./mosquitto/data:/mosquitto/data",
            "./mosquitto/log:/mosquitto/log"
        ],
        "networks": ["carros_net"]
    }
    compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "carros_net": {"driver": "bridge"}
        }
    }
    return compose

def generate_cars_compose(num_cars, mqtt_broker):
    discharge_rates = ["fast", "normal", "slow"]
    services = {}
    for i in range(1, num_cars + 1):
        discharge_rate = random.choice(discharge_rates)
        vehicle_id = f"car_{i}"
        services[f"car_{i}"] = {
            "build": {"context": "."},
            "command": f"python -u car.py {vehicle_id} {discharge_rate}",
            "environment": [
                f"MQTT_BROKER={mqtt_broker}",
                f"VEHICLE_ID=car{i}",
                f"DISCHARGE_RATE={discharge_rate}"
            ],
            "networks": ["carros_net"]
        }
    compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "carros_net": {"driver": "bridge"}
        }
    }
    return compose

if __name__ == "__main__":
    servers_port = CONST.servers_port

    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NUM_CARS
    mqtt_ip = CONST.mqtt_broker_ip
    mqtt_broker = os.getenv("MQTT_BROKER", mqtt_ip)

    servers_compose = generate_servers_compose(servers_port)
    cars_compose = generate_cars_compose(num_cars, mqtt_broker)

    with open("docker-compose.servers.yml", "w") as f:
        yaml.dump(servers_compose, f, sort_keys=False)
    with open("docker-compose.cars.yml", "w") as f:
        yaml.dump(cars_compose, f, sort_keys=False)

    print(f"Arquivos docker-compose.servers.yml e docker-compose.cars.yml gerados com {num_cars} carros.")
