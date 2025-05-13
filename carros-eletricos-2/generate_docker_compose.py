#!/usr/bin/env python3
import yaml
import random
<<<<<<< Updated upstream

def generate_docker_compose(num_cars):
    discharge_rates = ["fast", "normal", "slow"]
    services = {
        "server_a": {
            "build": ".",
            "command": "python server_a.py",
            "ports": ["5000:5000"],
            "volumes": ["./:/app"],
            "environment": ["FLASK_ENV=development"],
            "networks": ["charging_network"]
        },
        "server_b": {
            "build": ".",
            "command": "python server_b.py",
            "ports": ["5001:5001"],
            "volumes": ["./:/app"],
            "environment": ["FLASK_ENV=development"],
            "networks": ["charging_network"]
        },
        "server_c": {
            "build": ".",
            "command": "python server_c.py",
            "ports": ["5002:5002"],
            "volumes": ["./:/app"],
            "environment": ["FLASK_ENV=development"],
            "networks": ["charging_network"]
=======
from constants import servers_port

def generate_docker_compose(num_cars):
    discharge_rates = ["fast", "normal", "slow"]
    services = {}

    # Configurações padrão para todos os serviços
    base_config = {
        "build": ".",
        "volumes": ["./:/app"],
        "networks": ["charging_network"],
        "dns": ["8.8.8.8", "8.8.4.4"]  # DNS do Google
    }

    # 1. Gerar serviços para os servidores
    for server in servers_port:
        server_name = server["name"]
        port = server["port"]
        
        services[f"server_{server_name}"] = {
            **base_config,
            "command": f"python -u server_{server_name}.py",
            "ports": [f"{port}:{port}"],
            "environment": [
                "FLASK_ENV=development",
                "MQTT_BROKER=broker.hivemq.com",
                "MQTT_PORT=1883",
                f"SERVER_NAME={server_name}"
            ],
            "healthcheck": {
                "test": ["CMD", "curl", "-f", f"http://localhost:{port}/api/charging_points"],
                "interval": "10s",
                "timeout": "5s",
                "retries": 3
            }
>>>>>>> Stashed changes
        }
    }

<<<<<<< Updated upstream
    # Generate N car services
=======
    # 2. Gerar serviços para os carros
>>>>>>> Stashed changes
    for i in range(1, num_cars + 1):
        vehicle_id = f"vehicle_{i}"
        discharge_rate = random.choice(discharge_rates)
        
        services[f"car_{i}"] = {
<<<<<<< Updated upstream
            "build": ".",
            "command": f"python car.py {vehicle_id} {discharge_rate}",
            "volumes": ["./:/app"],
            "depends_on": ["server_a"],  # Ensure server_a is running
            "networks": ["charging_network"]
=======
            **base_config,
            "command": f"python -u car.py {vehicle_id} {discharge_rate}",
            "environment": [
                f"VEHICLE_ID={vehicle_id}",
                "MQTT_BROKER=broker.hivemq.com",
                "MQTT_PORT=1883",
                f"DISCHARGE_RATE={discharge_rate}"
            ],
            "depends_on": {
                f"server_{s['name']}": {"condition": "service_healthy"}
                for s in servers_port
            },
            "restart": "on-failure"
>>>>>>> Stashed changes
        }

    # 3. Opção: Broker MQTT local (descomente se quiser usar)
    # services["mosquitto"] = {
    #     "image": "eclipse-mosquitto",
    #     "ports": ["1883:1883"],
    #     "networks": ["charging_network"]
    # }

    docker_compose = {
        "version": "3.8",
        "services": services,
        "networks": {
            "charging_network": {
                "driver": "bridge"
            }
        }
    }

    with open("docker-compose.yml", "w") as f:
        yaml.dump(docker_compose, f, default_flow_style=False)

if __name__ == "__main__":
    import sys
<<<<<<< Updated upstream
    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else 5  # Default to 5 cars
=======
    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else 3
>>>>>>> Stashed changes
    generate_docker_compose(num_cars)
    print(f"Generated docker-compose.yml with {num_cars} cars")