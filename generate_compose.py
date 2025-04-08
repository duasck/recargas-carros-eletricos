import yaml
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--pontos', type=int, default=10, help='Número de pontos de recarga')
parser.add_argument('--clientes', type=int, default=5, help='Número de clientes')
args = parser.parse_args()

NUM_PONTOS = args.pontos
NUM_CLIENTES = args.clientes
INITIAL_PORT_PONTOS = 6000

gerar_clientes(NUM_CLIENTES)
salvar_dados()

services = {
    'nuvem': {
        'build': {
            'context': '.',
            'dockerfile': 'Dockerfile'
        },
        'container_name': 'nuvem',
        'volumes': ['.:/app'],
        'networks': ['rede_recarga'],
        'ports': ["5000:5000"],
        'command': ["python", "./nuvem.py"],
    }
}

for i in range(1, NUM_PONTOS + 1):
    services[f'ponto_{i}'] = {
        'build': {
            'context': '.',
            'dockerfile': 'Dockerfile'
        },
        'volumes': ['.:/app'],
        'networks': ['rede_recarga'],
        'command': ["python", "./ponto_recarga.py"],
        'environment': [
            "DOCKER_ENV=true",
            f"PORT={INITIAL_PORT_PONTOS + i}",
            f"PONTO_ID={i}"
        ]
    }

for i in range(1, NUM_CLIENTES + 1):
    services[f'cliente_{i}'] = {
        'build': {
            'context': '.',
            'dockerfile': 'Dockerfile'
        },
        'volumes': ['.:/app'],
        'depends_on': ['nuvem'],
        'networks': ['rede_recarga'],
        'command': ["python", "./cliente.py"],
        'environment': [
            "DOCKER_ENV=true",
            f"HOSTNAME=cliente_{i}"  # Para identificação no logging
        ]
    }

compose = {
    'version': '3.8',
    'services': services,
    'networks': {
        'rede_recarga': {
            'driver': 'bridge'
        }
    }
}

with open('docker-compose-generated.yml', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False)

print(f"Arquivo docker-compose-generated.yml gerado com {NUM_PONTOS} pontos e {NUM_CLIENTES} clientes.")