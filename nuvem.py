import socket
import threading
import logging
import json
import os
from collections import defaultdict
# from random import uniform  # Não está sendo usado
from config import get_host  # Está sendo usado para obter o host dos pontos

"""
TO-DO:
    - arrumar o histórico
"""

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NUVEM] %(message)s")

HOST = "0.0.0.0"
PORT = 5000
BASE_PORT = 6000  # Porta base para os pontos de recarga

def get_ponto_host(id_ponto):
    return f"ponto_{id_ponto[1:]}" if os.getenv('DOCKER_ENV') == "true" else "localhost"

# Geração dinâmica dos pontos de recarga
def gerar_pontos_recarga(num_pontos):
    pontos = {}
    base_lat = -23.5505
    base_lon = -46.6333
    
    for i in range(1, num_pontos + 1):
        pontos[f"P{i}"] = {
            "ip": f"ponto_{i}",  # Nome do serviço no Docker
            "porta": BASE_PORT + i,
            "localizacao": {
                "lat": base_lat + (i * 0.001),  # Pequeno incremento
                "lon": base_lon + (i * 0.001)
            },
            "status": "disponivel",
            "fila": [],  # Lista para armazenar IDs dos veículos na fila
            "veiculo_atual": None  # Veículo atualmente usando o ponto
        }
    return pontos

NUM_PONTOS = int(os.getenv('NUM_PONTOS', 1))  # Pega do compose ou usa 1 como padrão
PONTOS_RECARGA = gerar_pontos_recarga(NUM_PONTOS)

def calcular_pontos_proximos_com_fila(localizacao_cliente):
    pontos_proximos = []
    for id_ponto, info in PONTOS_RECARGA.items():
        distancia = calcular_distancia(localizacao_cliente, info["localizacao"])
        pontos_proximos.append({
            "id_ponto": id_ponto,
            "distancia": distancia,
            "status": info["status"],
            "localizacao": info["localizacao"],
            "tamanho_fila": len(info["fila"]),
            "pode_entrar_fila": True
        })
    pontos_proximos.sort(key=lambda x: (x["tamanho_fila"], x["distancia"]))
    return pontos_proximos[:5]

def calcular_pontos_proximos(localizacao_cliente):
    # Mantém a função original que só retorna pontos disponíveis
    pontos_proximos = []
    for id_ponto, info in PONTOS_RECARGA.items():
        if info["status"] == "disponivel":  # Filtra apenas pontos disponíveis
            distancia = calcular_distancia(localizacao_cliente, info["localizacao"])
            pontos_proximos.append({
                "id_ponto": id_ponto,
                "distancia": distancia,
                "status": info["status"],
                "localizacao": info["localizacao"]
            })
    pontos_proximos.sort(key=lambda x: x["distancia"])
    return pontos_proximos[:5]

def distribuir_clientes(pontos_proximos):
    for ponto in pontos_proximos:
        if ponto["status"] == "disponivel":
            return ponto["id_ponto"]
    return None

def atualizar_status_ponto(id_ponto, status):
    if id_ponto in PONTOS_RECARGA:
        PONTOS_RECARGA[id_ponto]["status"] = status
        return True
    return False

def handle_client(client_socket, addr):
    logging.info(f"Cliente {addr} conectado.")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                logging.info(f"Cliente {addr} desconectou.")
                break

            mensagem = json.loads(data.decode())
            logging.info(f"Mensagem recebida do cliente: {mensagem}")

            if mensagem["acao"] == "listar_pontos":
                # Lista apenas pontos disponíveis
                pontos_proximos = calcular_pontos_proximos(mensagem["localizacao"])
                client_socket.sendall(json.dumps(pontos_proximos).encode())

            elif mensagem["acao"] == "listar_pontos_com_fila":
                # Lista todos os pontos próximos, incluindo ocupados com informação da fila
                pontos_proximos = calcular_pontos_proximos_com_fila(mensagem["localizacao"])
                client_socket.sendall(json.dumps(pontos_proximos).encode())

            elif mensagem["acao"] == "solicitar_reserva":
                # Mantém o comportamento original - só tenta reservar pontos disponíveis
                pontos_proximos = calcular_pontos_proximos(mensagem["localizacao"])
                id_ponto = None
                
                for ponto in pontos_proximos:
                    if ponto["status"] == "disponivel":
                        id_ponto = ponto["id_ponto"]
                        break
                
                if id_ponto:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
                            ponto_host = get_host(f"ponto_{id_ponto[1:]}")
                            ponto_socket.connect((ponto_host, PONTOS_RECARGA[id_ponto]["porta"]))
                            ponto_socket.sendall(json.dumps({
                                "acao": "reservar",
                                "id_veiculo": mensagem["id_veiculo"]
                            }).encode())
                            resposta_ponto = ponto_socket.recv(1024)
                            
                            if json.loads(resposta_ponto.decode())["status"] == "reservado":
                                PONTOS_RECARGA[id_ponto]["status"] = "reservado"
                                PONTOS_RECARGA[id_ponto]["veiculo_atual"] = mensagem["id_veiculo"]
                            
                            client_socket.sendall(resposta_ponto)
                    except Exception as e:
                        logging.error(f"Erro ao conectar com ponto {id_ponto}: {e}")
                        client_socket.sendall(json.dumps({
                            "status": "erro",
                            "mensagem": str(e)
                        }).encode())
                else:
                    client_socket.sendall(json.dumps({
                        "status": "indisponivel",
                        "mensagem": "Nenhum ponto disponível"
                    }).encode())

            elif mensagem["acao"] == "entrar_fila":
                # Nova ação para entrar na fila de um ponto específico
                id_ponto = mensagem["id_ponto"]
                if id_ponto in PONTOS_RECARGA:
                    if mensagem["id_veiculo"] not in PONTOS_RECARGA[id_ponto]["fila"]:
                        PONTOS_RECARGA[id_ponto]["fila"].append(mensagem["id_veiculo"])
                        posicao_fila = len(PONTOS_RECARGA[id_ponto]["fila"])
                        client_socket.sendall(json.dumps({
                            "status": "fila",
                            "mensagem": f"Adicionado à fila do ponto {id_ponto}",
                            "posicao_fila": posicao_fila
                        }).encode())
                    else:
                        client_socket.sendall(json.dumps({
                            "status": "erro",
                            "mensagem": "Veículo já está na fila deste ponto"
                        }).encode())
                else:
                    client_socket.sendall(json.dumps({
                        "status": "erro",
                        "mensagem": "Ponto não encontrado"
                    }).encode())

            elif mensagem["acao"] == "liberar_ponto":
                id_ponto = mensagem["id_ponto"]
                if id_ponto in PONTOS_RECARGA:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
                            ponto_host = get_host(f"ponto_{id_ponto[1:]}")
                            ponto_socket.connect((ponto_host, PONTOS_RECARGA[id_ponto]["porta"]))
                            ponto_socket.sendall(json.dumps({
                                "acao": "liberar",
                                "id_veiculo": mensagem.get("id_veiculo", "")
                            }).encode())
                            resposta = ponto_socket.recv(1024)
                            
                            if json.loads(resposta.decode())["status"] == "liberado":
                                PONTOS_RECARGA[id_ponto]["status"] = "disponivel"
                            
                            client_socket.sendall(resposta)
                    except Exception as e:
                        logging.error(f"Erro ao liberar ponto {id_ponto}: {e}")
                        client_socket.sendall(json.dumps({
                            "status": "erro",
                            "mensagem": str(e)
                        }).encode())
                else:
                    client_socket.sendall(json.dumps({
                        "status": "erro",
                        "mensagem": "Ponto não encontrado"
                    }).encode())

            elif mensagem["acao"] == "solicitar_historico":
                # Implementação fictícia - pode ser conectada a um banco de dados real
                historico = [{
                    "data": "2023-10-01",
                    "valor": 50.0,
                    "ponto": "P1"
                }, {
                    "data": "2023-10-05",
                    "valor": 30.0,
                    "ponto": "P2"
                }]
                client_socket.sendall(json.dumps(historico).encode())

    except Exception as e:
        logging.error(f"Erro ao processar cliente {addr}: {e}")
    finally:
        client_socket.close()
        logging.info(f"Conexão com {addr} encerrada.")

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    logging.info(f"Servidor rodando na porta {PORT}...")

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

if __name__ == "__main__":
    main()
