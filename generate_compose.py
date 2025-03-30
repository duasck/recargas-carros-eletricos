import yaml

NUM_PONTOS = 10  # Ou receba como argumento

services = {
    'nuvem': {
        'build': '.',
        'container_name': 'nuvem',
        'networks': ['rede_recarga'],
        'ports': ["5000:5000"],
        'command': ["python", "/app/nuvem.py"],
        'environment': [f"NUM_PONTOS={NUM_PONTOS}"]
    }
}

# Adiciona pontos
for i in range(1, NUM_PONTOS + 1):
    services[f'ponto_{i}'] = {
        'build': '.',
        'networks': ['rede_recarga'],
        'command': ["python", "/app/ponto_recarga.py"],
        'environment': [
            f"PORT={6000 + i}",
            f"PONTO_ID={i}"
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
    yaml.dump(compose, f)