#!/usr/bin/python
import sys
import os
import yaml
import json
import global_utils.constants as CONST
import random

# carrega as configurações
try:
    with open("keys.json", "r") as f:
        KEYS = json.load(f)
    COMPANY_PRIVATE_KEYS = {c["name"]: c["private_key"] for c in KEYS["companies"]}
    VEHICLE_PRIVATE_KEYS = {v["id"]: v["private_key"] for v in KEYS["vehicles"]}
except FileNotFoundError:
    print("Aviso: keys.json não encontrado. Gerando chaves placeholder.")
    COMPANY_PRIVATE_KEYS = {f"company_{chr(97+i)}": "0xPlaceholderKey" for i in range(5)}
    VEHICLE_PRIVATE_KEYS = {f"car_{i+1}": "0xPlaceholderVehicleKey" for i in range(5)}

try:
    with open("network_config.json", "r") as f:
        NET_CONFIG = json.load(f)
    print("INFO: network_config.json encontrado. Gerando arquivos para modo distribuído (laboratório).")
except FileNotFoundError:
    NET_CONFIG = {}
    print("INFO: network_config.json não encontrado. Certifique-se de criá-lo para o modo de laboratório.")


# funções geradoras
def generate_infra_compose():
    """Gera o docker-compose para os serviços de infraestrutura (geth, mosquitto, api)."""
    services = {}
    
    # Serviço Geth
    services["geth"] = {
        "build": {"context": "./geth_custom"},
        "container_name": "geth",
        "ports": ["8545:8545", "30303:30303"],
        "command": "--dev --http --http.addr 0.0.0.0 --http.api eth,net,web3,personal,admin --http.corsdomain=* --http.vhosts=* --allow-insecure-unlock",
        "networks": ["lab_net"],
        "healthcheck": {
            "test": ["CMD-SHELL", "nc -z localhost 8545 || exit 1"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10
        }
    }
    
    # Serviço Mosquitto
    services["mosquitto"] = {
        "image": "eclipse-mosquitto",
        "container_name": "mosquitto",
        "ports": ["18833:18833", "9001:9001"],
        "volumes": ["./mosquitto/config:/mosquitto/config", "./mosquitto/data:/mosquitto/data", "./mosquitto/log:/mosquitto/log"],
        "networks": ["lab_net"],
        "healthcheck": {
            "test": ["CMD-SHELL", "nc -z localhost 18833 || exit 1"],
            "interval": "10s",
            "timeout": "5s",
            "retries": 5
        }
    }
    
    # Serviço da API de Transações
    services["transactions_api"] = {
        "build": {"context": "."},
        "command": "python api/transactions.py",
        "container_name": "transactions_api",
        "ports": ["5100:5100"],
        "networks": ["lab_net"],
        "environment": [
            "ETH_NODE_URL=http://geth:8545" # Usa o nome do serviço, pois está no mesmo compose
        ],
        "depends_on": {
            "geth": {"condition": "service_healthy"}
        },
        "volumes": ["./blockchain:/app/blockchain"]
    }

    return {"services": services, "networks": {"lab_net": {"driver": "bridge"}}}

def generate_server_compose(server_name_short):
    """Gera o docker-compose para um servidor específico."""
    server_info = next((s for s in CONST.servers_port if s["name"] == server_name_short), None)
    if not server_info:
        raise ValueError(f"Servidor '{server_name_short}' não encontrado em constants.py")

    company_full_name = server_info["company"]
    services = {}

    if company_full_name == 'company_a':
        services["contract_deploy"] = {
            "build": {"context": "."},
            "command": "python blockchain/deploy_contract.py",
            "container_name": "contract_deploy",
            "environment": [
                f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url')}",
                f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get('company_a')}"
            ],
            "volumes": ["./blockchain:/app/blockchain"]
        }

    services[f"server_{server_name_short}"] = {
        "build": {"context": "."},
        "command": f"python servers/server_{server_name_short}.py",
        "container_name": f"server_{server_name_short}",
        "ports": [f"{server_info['port']}:{server_info['port']}"],
        "environment": [
            f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url')}",
            f"MQTT_BROKER={NET_CONFIG.get('mqtt_broker')}",
            f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get(company_full_name)}"
        ],
        "volumes": ["./blockchain:/app/blockchain"]
    }
    
    if company_full_name == 'company_a':
        services[f"server_{server_name_short}"]["depends_on"] = {
            "contract_deploy": {"condition": "service_completed_successfully"}
        }

    return {"services": services}

def generate_cars_compose_distributed(num_cars):
    """Gera o docker-compose para os carros em modo distribuído."""
    services = {}
    for i in range(1, num_cars + 1):
        vehicle_id = f"car_{i}"
        services[vehicle_id] = {
            "build": {"context": "."},
            "command": f"python -u car.py {vehicle_id} {random.choice(['fast', 'normal', 'slow'])}",
            "container_name": vehicle_id,
            "environment": [
                f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url')}",
                f"MQTT_BROKER={NET_CONFIG.get('mqtt_broker')}",
                f"MQTT_PORT={NET_CONFIG.get('mqtt_port', 18833)}",
                f"VEHICLE_PRIVATE_KEY={VEHICLE_PRIVATE_KEYS.get(vehicle_id)}"
            ],
            "volumes": ["./blockchain:/app/blockchain"]
        }
    return {"services": services}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: ./generate_compose.py <perfil> [opções]")
        print("Perfis disponíveis: infra, server, cars")
        sys.exit(1)

    profile = sys.argv[1]

    if profile == "infra":
        print("Gerando docker-compose.infra.yml...")
        compose_data = generate_infra_compose()
        with open("docker-compose.infra.yml", "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        print("Arquivo gerado com sucesso.")

    elif profile == "server":
        if len(sys.argv) < 3:
            print("Uso: ./generate_compose.py server <nome_curto> (ex: a, b, c)")
            sys.exit(1)
        server_name = sys.argv[2]
        filename = f"docker-compose.server_{server_name}.yml"
        print(f"Gerando {filename}...")
        compose_data = generate_server_compose(server_name)
        with open(filename, "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        print("Arquivo gerado com sucesso.")
        
    elif profile == "cars":
        try:
            num_cars = int(sys.argv[2])
        except (IndexError, ValueError):
            num_cars = 3 
        
        filename = "docker-compose.cars.yml"
        print(f"Gerando {filename} para {num_cars} carros em modo distribuído...")
        compose_data = generate_cars_compose_distributed(num_cars)
        with open(filename, "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        print("Arquivo gerado com sucesso.")

    else:
        print(f"Perfil desconhecido: '{profile}'. Perfis disponíveis: infra, server, cars.")
        sys.exit(1)
