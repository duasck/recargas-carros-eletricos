import yaml
import random

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
        }
    }

    # Generate N car services
    for i in range(1, num_cars + 1):
        vehicle_id = f"vehicle_{i}"
        discharge_rate = random.choice(discharge_rates)
        services[f"car_{i}"] = {
            "build": ".",
            "command": f"python car.py {vehicle_id} {discharge_rate}",
            "volumes": ["./:/app"],
            "depends_on": ["server_a"],  # Ensure server_a is running
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
    num_cars = int(sys.argv[1]) if len(sys.argv) > 1 else 5  # Default to 5 cars
    generate_docker_compose(num_cars)
    print(f"Generated docker-compose.yml with {num_cars} cars")