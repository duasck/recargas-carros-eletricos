import socket
import threading
import logging
import json
import os
from random import uniform

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NUVEM] %(message)s")

HOST = "0.0.0.0"
PORT = 5000
def load_points(data_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

#transfere os pontos criados e salvos no json para uma lista
pontos = load_points('./dados_pontos.json')

#isso aqui tá sendo usado??
def gerar_pontos_recarga(num_pontos):
    pontos = {}
    base_lat = -23.5505
    base_lon = -46.6333
    
    for i in range(1, num_pontos + 1):
        pontos[f"P{i}"] = {
            "ip": f"ponto_{i}",
            "porta": 6000 + i,
            "localizacao": {
                "lat": base_lat + (i * 0.01),
                "lon": base_lon + (i * 0.01)
            },
            "status": "disponivel"
        }
    return pontos

NUM_PONTOS = int(os.getenv('NUM_PONTOS', 3))
PONTOS_RECARGA = load_points('./dados_pontos.json')

def calcular_distancia(local1, local2):
    # Simulação simplificada de cálculo de distância
    return ((local1["lat"] - local2["lat"])**2 + (local1["lon"] - local2["lon"])**2)**0.5

def calcular_pontos_proximos(localizacao_cliente):
    pontos_proximos = []
    for id_ponto, info in PONTOS_RECARGA.items():
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

#onde ocorre a comunicação com o cliente
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
                pontos_proximos = calcular_pontos_proximos(mensagem["localizacao"])
                client_socket.sendall(json.dumps(pontos_proximos).encode())

            elif mensagem["acao"] == "solicitar_reserva":
                id_ponto = distribuir_clientes(calcular_pontos_proximos(mensagem["localizacao"]))
                if id_ponto:
                    ip_ponto = PONTOS_RECARGA[id_ponto]["ip"]
                    porta_ponto = PONTOS_RECARGA[id_ponto]["porta"]
                    
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
                            ponto_socket.connect((ip_ponto, porta_ponto))
                            ponto_socket.sendall(json.dumps({
                                "acao": "reservar",
                                "id_veiculo": mensagem["id_veiculo"]
                            }).encode())
                            resposta_ponto = ponto_socket.recv(1024)
                            
                        if json.loads(resposta_ponto.decode())["status"] == "reservado":
                            atualizar_status_ponto(id_ponto, "ocupado")
                        
                        client_socket.sendall(resposta_ponto)
                    except Exception as e:
                        logging.error(f"Erro ao conectar com ponto {id_ponto}: {e}")
                        client_socket.sendall(json.dumps({
                            "status": "erro",
                            "mensagem": "Falha na conexão com o ponto de recarga"
                        }).encode())
                else:
                    client_socket.sendall(json.dumps({
                        "status": "indisponivel",
                        "mensagem": "Nenhum ponto disponível"
                    }).encode())

            elif mensagem["acao"] == "liberar_ponto":
                if atualizar_status_ponto(mensagem["id_ponto"], "disponivel"):
                    client_socket.sendall(json.dumps({"status": "liberado"}).encode())
                else:
                    client_socket.sendall(json.dumps({"status": "erro"}).encode())

            elif mensagem["acao"] == "solicitar_historico":
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