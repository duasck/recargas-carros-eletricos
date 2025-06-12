import sys
import os
import yaml
import constants as CONST
import random
import json
DEFAULT_NUM_CARS = 5

with open("keys.json", "r") as f:
    KEYS = json.load(f)
    COMPANY_PRIVATE_KEYS = {c["name"]: c["private_key"] for c in KEYS["companies"]}
    VEHICLE_PRIVATE_KEYS = {v["id"]: v["private_key"] for v in KEYS["vehicles"]}
    DEPLOYER_PRIVATE_KEY = KEYS["deployer"]["private_key"]


def generate_servers_compose(servers_port):
    with open("keys.json", "r") as f:
        keys = json.load(f)

    services = {}
    
    # Adicionar Geth primeiro com healthcheck
    services["geth"] = {
        "image": "ethereum/client-go",
        "container_name": "geth",
        "ports": ["8545:8545", "30303:30303"],
        "command": "--dev --http --http.addr 0.0.0.0 --http.api eth,net,web3,personal,miner,txpool --http.corsdomain=* --http.vhosts=* --allow-insecure-unlock",
        "networks": ["carros_net"],
        "healthcheck": {
            "test": ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8545"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5,
            "start_period": "30s"
        }
    }
    
    # Contract deploy
    services["contract_deploy"] = {
        "build": {"context": "."},
        "command": "python blockchain/deploy_contract.py",
        "container_name": "contract_deploy",
        "networks": ["carros_net"],
        "depends_on": {
            "geth": {"condition": "service_healthy"}
        },
        "environment": [
            f"PRIVATE_KEY={DEPLOYER_PRIVATE_KEY}",
            "ETH_NODE_URL=http://geth:8545"
        ]
    }

    # Servidores das empresas
    for s in servers_port:
        company_private_keys = {c["name"]: c["private_key"] for c in keys["companies"]}
        company_addresses = {d["name"]: d["address"] for d in keys["companies"]}
        company_key = f"company_{s['name']}"
        company = s["name"].lower()
        port = s["port"]

        contract_address = os.getenv("CONTRACT_ADDRESS") or company_addresses[company_key]

        services[f"server_{company}"] = {
            "build": {"context": "."},
            "command": f"python servers/server_{company}.py",
            "container_name": f"server_{company}",
            "ports": [f"{port}:{port}"],
            "networks": ["carros_net"],
            "environment": [
                f"CONTRACT_ADDRESS={contract_address}",
                f"PRIVATE_KEY={company_private_keys[company_key]}",
                "ETH_NODE_URL=http://geth:8545"
            ],
            "depends_on": {
                "contract_deploy": {"condition": "service_completed_successfully"}
            }
        }
    
    # Transactions API
    services["transactions_api"] = {
        "build": {"context": "."},
        "command": "python transactions.py",
        "container_name": "transactions_api",
        "ports": ["5100:5100"],
        "networks": ["carros_net"],
        "depends_on": {
            "contract_deploy": {"condition": "service_completed_successfully"}
        },
        "environment": [
            f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', 'None')}",
            "ETH_NODE_URL=http://geth:8545"
        ]
    }
    
    compose = {
        "services": services,
        "networks": {
            "carros_net": {"driver": "bridge"}
        }
    }
    return compose


def generate_cars_compose(num_cars, mqtt_broker):
    with open("keys.json", "r") as f:
        keys = json.load(f)
    vehicle_private_keys = {v["id"]: v["private_key"] for v in keys["vehicles"]}
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
                f"CONTRACT_ADDRESS={os.getenv('CONTRACT_ADDRESS', 'None')}",
                f"VEHICLE_PRIVATE_KEY={vehicle_private_keys.get(f'car_{i}', '0xDefaultKey')}",
                "ETH_NODE_URL=http://geth:8545"
            ],
            "networks": ["carros_net"],
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
    mqtt_broker = os.getenv("MQTT_BROKER", "broker.hivemq.com")

    servers_compose = generate_servers_compose(servers_port)
    cars_compose = generate_cars_compose(num_cars, mqtt_broker)

    with open("docker-compose.servers.yml", "w") as f:
        yaml.dump(servers_compose, f, sort_keys=False)
    with open("docker-compose.cars.yml", "w") as f:
        yaml.dump(cars_compose, f, sort_keys=False)

    print(f"Arquivos docker-compose.servers.yml e docker-compose.cars.yml gerados com {num_cars} carros.")