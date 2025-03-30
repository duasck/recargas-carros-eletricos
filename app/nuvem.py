import socket
import threading
import logging
import json

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NUVEM] %(message)s")

HOST = "0.0.0.0"
PORT = 5000

# configurar para gerar isso automaticamente
PONTOS_RECARGA = {
    "P1": {"ip": "ponto1", "porta": 6001, "localizacao": {"lat": -23.5505, "lon": -46.6333}, "status": "disponivel"},
    "P2": {"ip": "ponto2", "porta": 6002, "localizacao": {"lat": -23.5615, "lon": -46.6553}, "status": "disponivel"},
    "P3": {"ip": "ponto3", "porta": 6003, "localizacao": {"lat": -23.5705, "lon": -46.6433}, "status": "disponivel"}
}

def calcular_distancia(local1, local2):
    # Simulação de cálculo de distância (pode ser substituído por uma função real)
    return abs(local1["lat"] - local2["lat"]) + abs(local1["lon"] - local2["lon"])

def calcular_pontos_proximos(localizacao_cliente):
    pontos_proximos = []
    for id_ponto, info in PONTOS_RECARGA.items():
        distancia = calcular_distancia(localizacao_cliente, info["localizacao"])
        pontos_proximos.append({"id_ponto": id_ponto, "distancia": distancia, "status": info["status"]})
    pontos_proximos.sort(key=lambda x: x["distancia"])
    return pontos_proximos[:5]  # Retorna os 5 mais próximos

def distribuir_clientes(pontos_proximos):
    for ponto in pontos_proximos:
        if ponto["status"] == "disponivel":
            return ponto["id_ponto"]
    return None

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
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
                        ponto_socket.connect((ip_ponto, porta_ponto))
                        ponto_socket.sendall(json.dumps({"acao": "reservar", "id_veiculo": mensagem["id_veiculo"]}).encode())
                        resposta_ponto = ponto_socket.recv(1024)
                    client_socket.sendall(resposta_ponto)
                else:
                    client_socket.sendall(json.dumps({"status": "indisponivel"}).encode())

            elif mensagem["acao"] == "solicitar_historico":
                # Simulação de histórico (pode ser substituído por um banco de dados real)
                historico = [{"data": "2023-10-01", "valor": 50.0}, {"data": "2023-10-05", "valor": 30.0}]
                client_socket.sendall(json.dumps(historico).encode())

    except Exception as e:
        logging.error(f"Erro ao processar cliente {addr}: {e}")
    finally:
        client_socket.close()
        logging.info(f"Conexão com {addr} encerrada.")

# Inicializa o servidor
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

logging.info(f"Servidor rodando na porta {PORT}...")

while True:
    client_socket, addr = server_socket.accept()
    threading.Thread(target=handle_client, args=(client_socket, addr)).start()