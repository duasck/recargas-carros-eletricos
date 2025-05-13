#!/usr/bin/env python3
import yaml
import random
from constants import servers_port 

def generate_docker_compose(num_cars):
    discharge_rates = ["fast", "normal", "slow"]
    services = {}

    # Gerar serviços para os servidores dinamicamente
    servers = servers_port
    for i, server in enumerate(servers):
        server_name = server["name"]
        port = server["port"]
        services[f"server_{server_name}"] = {
            "build": ".",
            "command": f"python -u server_{server_name}.py",  # Usar -u para saída não bufferizada
            "ports": [f"{port}:{port}"],
            "volumes": ["./:/app"],
            "environment": [
                "FLASK_ENV=development",
                "MQTT_BROKER=broker.hivemq.com",
                "MQTT_PORT=1883",
                f"SERVER_NAME={server_name}"
            ],
            "networks": ["charging_network"]
        }

    # Gerar serviços para os carros
    for i in range(1, num_cars + 1):
        vehicle_id = f"vehicle_{i}"
        discharge_rate = random.choice(discharge_rates)
        services[f"car_{i}"] = {
            "build": ".",
            "command": f"python -u car.py {vehicle_id} {discharge_rate}",  # Usar -u para saída não bufferizada
            "volumes": ["./:/app"],
            "environment": [
                f"VEHICLE_ID={vehicle_id}",
                "MQTT_BROKER=broker.hivemq.com",
                "MQTT_PORT=1883",
                f"DISCHARGE_RATE={discharge_rate}"
            ],
            "depends_on": [f"server_{s['name']}" for s in servers],  # Dependência de todos os servidores
            "networks": ["charging_network"]
        }

    docker_compose = {
        "version": "3.8",
        "services": services,
        "networks": {"charging_network": {"driver": "bridge"}}
    }

    with open("docker-compose.yml", "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)

if __name__ == "__main__":
    import sys
    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else 3  # Default to 3 cars
    generate_docker_compose(num_cars)
    print(f"Generated docker-compose.yml with {num_cars} cars")