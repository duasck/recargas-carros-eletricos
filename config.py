import os

def is_docker():
    """Detecta se está rodando dentro de um container Docker"""
    return os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV') == "true"

def get_host(service_name):
    """Retorna o host correto baseado no ambiente"""
    return service_name if is_docker() else "localhost"