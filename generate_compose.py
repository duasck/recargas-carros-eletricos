#!/usr/bin/python
import sys
import os
import yaml
import json
import global_utils.constants as CONST
import random

DEFAULT_NUM_CARS = 5

# Carregar chaves do keys.json, se disponível
try:
    with open("keys.json", "r") as f:
        KEYS = json.load(f)
    COMPANY_PRIVATE_KEYS = {c["name"]: c["private_key"] for c in KEYS["companies"]}
    VEHICLE_PRIVATE_KEYS = {v["id"]: v["private_key"] for v in KEYS["vehicles"]}
except FileNotFoundError:
    print("Aviso: keys.json não encontrado. Usando chaves placeholder.")
    COMPANY_PRIVATE_KEYS = {f"company_{chr(97+i)}": "0xPlaceholderKey" for i in range(5)}
    VEHICLE_PRIVATE_KEYS = {f"car_{i+1}": "0xPlaceholderVehicleKey" for i in range(5)}

def generate_servers_compose(servers_port):
    services = {}
    for s in servers_port:
        company = s["name"].lower()
        company_full_name = s["company"]
        port = s["port"]
        services[f"server_{company}"] = {
            "build": {"context": "."},
            "command": f"python servers/server_{company}.py",
            "container_name": f"server_{company}",
            "ports": [f"{port}:{port}"],
            "networks": ["carros_net"],
            "environment": [
                f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', '')}",
                f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get(company_full_name, '0xPlaceholderKey')}",
                "MQTT_BROKER=mosquitto"
            ],
            "depends_on": {
                "geth": {"condition": "service_healthy"},
                "mosquitto": {"condition": "service_healthy"},
                "contract_deploy": {"condition": "service_completed_successfully"}
            },
            "volumes": [
                "./blockchain:/app/blockchain"
            ]
        }

    services["geth"] = {
        "build": {
            "context": "./geth_custom"
        },
        "container_name": "geth",
        "ports": ["8545:8545", "30303:30303"],
        # --- CORREÇÃO AQUI ---
        # Removendo o prefixo "http." da flag, o nome correto é --allow-insecure-unlock
        "command": "--dev --http --http.addr 0.0.0.0 --http.api eth,net,web3,personal,admin --http.corsdomain=* --http.vhosts=* --allow-insecure-unlock",
        "networks": ["carros_net"],
        "healthcheck": {
            "test": ["CMD-SHELL", "nc -z localhost 8545 || exit 1"],
            "interval": "5s",
            "timeout": "5s",
            "retries": 25,
            "start_period": "15s"
        }
    }

    services["mosquitto"] = {
        "image": "eclipse-mosquitto",
        "container_name": "mosquitto",
        "ports": ["18833:18833", "9001:9001"],
        "volumes": [
            "./mosquitto/config:/mosquitto/config",
            "./mosquitto/data:/mosquitto/data",
            "./mosquitto/log:/mosquitto/log"
        ],
        "networks": ["carros_net"],
        "healthcheck": {
            "test": ["CMD-SHELL", "nc -z localhost 18833 || exit 1"],
            "interval": "5s",
            "timeout": "5s",
            "retries": 10
        },
        "restart": "unless-stopped"
    }
    services["contract_deploy"] = {
        "build": {"context": "."},
        "command": "python blockchain/deploy_contract.py",
        "container_name": "contract_deploy",
        "networks": ["carros_net"],
        "environment": [
            f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', '')}",
            f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get('company_a', '0xPlaceholderKey')}"
        ],
        "depends_on": {
            "geth": {"condition": "service_healthy"}
        },
        "volumes": [
            "./blockchain:/app/blockchain"
        ]
    }
    services["transactions_api"] = {
        "build": {"context": "."},
        "command": "python transactions.py",
        "container_name": "transactions_api",
        "ports": ["5100:5100"],
        "networks": ["carros_net"],
        "environment": [
            f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', '')}"
        ],
        "depends_on": {
            "geth": {"condition": "service_healthy"},
            "mosquitto": {"condition": "service_healthy"},
            "contract_deploy": {"condition": "service_completed_successfully"}
        },
        "volumes": [
            "./blockchain:/app/blockchain"
        ]
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
                f"DISCHARGE_RATE={discharge_rate}",
                f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', '')}",
                f"VEHICLE_PRIVATE_KEY={VEHICLE_PRIVATE_KEYS.get(f'car_{i}', '0xPlaceholderVehicleKey')}"
            ],
            "networks": ["carros_net"],
            "depends_on": {
                "geth": {"condition": "service_healthy"},
                "mosquitto": {"condition": "service_healthy"},
                "contract_deploy": {"condition": "service_completed_successfully"}
            },
            "volumes": [
                "./blockchain:/app/blockchain"
            ]
        }
    compose = {
        "services": services,
        "networks": {
            "carros_net": {"driver": "bridge"}
        }
    }
    return compose

if __name__ == "__main__":
    servers_port = CONST.servers_port
    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NUM_CARS
    mqtt_broker = os.getenv("MQTT_BROKER", "mosquitto")

    servers_compose = generate_servers_compose(servers_port)
    cars_compose = generate_cars_compose(num_cars, mqtt_broker)

    with open("docker-compose.servers.yml", "w") as f:
        yaml.dump(servers_compose, f, sort_keys=False)
    with open("docker-compose.cars.yml", "w") as f:
        yaml.dump(cars_compose, f, sort_keys=False)

    print(f"Arquivos docker-compose.servers.yml e docker-compose.cars.yml gerados com {num_cars} carros.")
