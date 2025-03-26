import socket
import logging
import json

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [CLIENTE] %(message)s")

HOST = "nuvem"  # Nome do serviço da nuvem no Docker
PORT = 5000     # Porta da Nuvem

try:
    logging.info("Iniciando conexão com a Nuvem...")
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, PORT))
    logging.info("Conectado à Nuvem.")

    # mensagem = "Solicitação de recarga - Veículo ABC123"
    veiculo = {
        'id': '123',
        'position': [2, 3]
    }
    
    mensagem = json.dumps(veiculo)

    logging.info(f"Enviando mensagem: {veiculo}")
    client_socket.sendall(mensagem.encode())

    resposta = client_socket.recv(1024)
    logging.info(f"Resposta da Nuvem: {resposta.decode()}")

except Exception as e:
    logging.error(f"Erro no cliente: {e}")

finally:
    client_socket.close()
    logging.info("Conexão encerrada.")
