#!/usr/bin/python
import sys
import os
import yaml
import json
import global_utils.constants as CONST
import random

# --- CARREGAR CONFIGURAÇÕES ---
try:
    with open("keys.json", "r") as f:
        KEYS = json.load(f)
    COMPANY_PRIVATE_KEYS = {c["name"]: c["private_key"] for c in KEYS["companies"]}
    VEHICLE_PRIVATE_KEYS = {v["id"]: v["private_key"] for v in KEYS["vehicles"]}
except FileNotFoundError:
    print("Aviso: keys.json não encontrado. Usando chaves placeholder.")
    # Placeholders...

try:
    with open("network_config.json", "r") as f:
        NET_CONFIG = json.load(f)
    DISTRIBUTED_MODE = True
except FileNotFoundError:
    NET_CONFIG = {}
    DISTRIBUTED_MODE = False

# --- FUNÇÕES GERADORAS ---

def generate_infra_compose():
    """Gera o docker-compose para os serviços de infraestrutura (geth, mosquitto)."""
    services = {}
    services["geth"] = {
        "build": {"context": "./geth_custom"},
        "container_name": "geth",
        "ports": ["8545:8545", "30303:30303"],
        "command": "--dev --http --http.addr 0.0.0.0 --http.api eth,net,web3,personal,admin --http.corsdomain=* --http.vhosts=* --allow-insecure-unlock",
        "networks": ["lab_net"], # Usando uma rede diferente para clareza
    }
    services["mosquitto"] = {
        "image": "eclipse-mosquitto",
        "container_name": "mosquitto",
        "ports": ["18833:18833", "9001:9001"],
        "volumes": ["./mosquitto/config:/mosquitto/config", "./mosquitto/data:/mosquitto/data", "./mosquitto/log:/mosquitto/log"],
        "networks": ["lab_net"],
    }
    return {"services": services, "networks": {"lab_net": {"driver": "bridge"}}}

def generate_server_compose(server_name_short):
    """Gera o docker-compose para um servidor específico."""
    server_info = next((s for s in CONST.servers_port if s["name"] == server_name_short), None)
    if not server_info:
        raise ValueError(f"Servidor '{server_name_short}' não encontrado em constants.py")

    company_full_name = server_info["company"]
    services = {}

    # O primeiro servidor (e apenas ele) é responsável por implantar o contrato
    if company_full_name == 'company_a':
        services["contract_deploy"] = {
            "build": {"context": "."},
            "command": "python blockchain/deploy_contract.py",
            "environment": [
                f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url', 'http://geth:8545')}",
                f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get('company_a')}"
            ],
            "volumes": ["./blockchain:/app/blockchain"]
        }

    services[f"server_{server_name_short}"] = {
        "build": {"context": "."},
        "command": f"python servers/server_{server_name_short}.py",
        "ports": [f"{server_info['port']}:{server_info['port']}"],
        "environment": [
            f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url', 'http://geth:8545')}",
            f"MQTT_BROKER={NET_CONFIG.get('mqtt_broker', 'mosquitto')}",
            f"PRIVATE_KEY={COMPANY_PRIVATE_KEYS.get(company_full_name)}"
            # O endereço do contrato será lido do volume compartilhado
        ],
        "volumes": ["./blockchain:/app/blockchain"]
    }
    
    if company_full_name == 'company_a':
        services[f"server_{server_name_short}"]["depends_on"] = {
            "contract_deploy": {"condition": "service_completed_successfully"}
        }

    return {"services": services}


def generate_local_simulation_compose():
    """Gera os arquivos para a simulação local completa (o comportamento antigo)."""
    # Esta função pode reusar as funções que você já tinha ou ser reescrita
    # para combinar as peças. Por simplicidade, vou chamar a sua função original
    # que já está correta para este modo.
    from old_generate_compose import generate_servers_compose, generate_cars_compose # Supondo que você renomeou o antigo
    
    servers_port = CONST.servers_port
    num_cars = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    mqtt_broker = "mosquitto"
    
    servers_compose = generate_servers_compose(servers_port) # Chamar a função antiga
    cars_compose = generate_cars_compose(num_cars, mqtt_broker) # Chamar a função antiga
    
    with open("docker-compose.servers.yml", "w") as f:
        yaml.dump(servers_compose, f, sort_keys=False)
    with open("docker-compose.cars.yml", "w") as f:
        yaml.dump(cars_compose, f, sort_keys=False)
    print("Arquivos de simulação local gerados.")


# --- LÓGICA PRINCIPAL DO SCRIPT ---

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: ./generate_compose.py <perfil> [opções]")
        print("Perfis disponíveis: local, infra, server, cars")
        sys.exit(1)

    profile = sys.argv[1]

    if profile == "local":
        print("Gerando arquivos para simulação local...")
        # Para evitar reescrever, vamos assumir que seu script original que funciona
        # foi renomeado para 'original_generator.py' ou algo assim, e o chamamos.
        # Se preferir, pode-se integrar a lógica aqui.
        print("Modo 'local' precisa ser implementado ou chamado de um script separado.")
        print("Gerando arquivos para o modo de laboratório por enquanto.")

    elif profile == "infra":
        print("Gerando docker-compose.infra.yml...")
        compose_data = generate_infra_compose()
        with open("docker-compose.infra.yml", "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        print("Arquivo gerado com sucesso.")

    elif profile == "server":
        if len(sys.argv) < 3:
            print("Uso: ./generate_compose.py server <nome_curto_do_servidor> (ex: a, b, c)")
            sys.exit(1)
        server_name = sys.argv[2]
        filename = f"docker-compose.server_{server_name}.yml"
        print(f"Gerando {filename}...")
        compose_data = generate_server_compose(server_name)
        with open(filename, "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        print("Arquivo gerado com sucesso.")
        
    else:
        print(f"Perfil desconhecido: '{profile}'")
        sys.exit(1)

    def generate_cars_compose_distributed(num_cars):
        """Gera o docker-compose para os carros em modo distribuído."""
        services = {}
        for i in range(1, num_cars + 1):
            vehicle_id = f"car_{i}"
            services[f"car_{i}"] = {
                "build": {"context": "."},
                "command": f"python -u car.py {vehicle_id} {random.choice(['fast', 'normal', 'slow'])}",
                "environment": [
                    # Apontando para os IPs da configuração de rede
                    f"ETH_NODE_URL={NET_CONFIG.get('eth_node_url')}",
                    f"MQTT_BROKER={NET_CONFIG.get('mqtt_broker')}",
                    f"MQTT_PORT={NET_CONFIG.get('mqtt_port')}",
                    f"VEHICLE_PRIVATE_KEY={VEHICLE_PRIVATE_KEYS.get(vehicle_id)}"
                ],
                "volumes": [
                    "./blockchain:/app/blockchain" # Para ler os artefatos do contrato
                ]
            }
        return {"services": services}

        # Adicionar um novo `elif` para o perfil 'cars'
        elif profile == "cars":
            try:
                num_cars = int(sys.argv[2])
            except (IndexError, ValueError):
                num_cars = 3 # Padrão de 3 carros se não for especificado
            
            filename = "docker-compose.cars.yml"
            print(f"Gerando {filename} para {num_cars} carros em modo distribuído...")
            compose_data = generate_cars_compose_distributed(num_cars)
            with open(filename, "w") as f:
                yaml.dump(compose_data, f, sort_keys=False)
            print("Arquivo gerado com sucesso.")

        else:
            print(f"Perfil desconhecido: '{profile}'")
            sys.exit(1)
