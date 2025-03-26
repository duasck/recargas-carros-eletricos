import socket
import threading
import logging
import json

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [NUVEM] %(message)s")

HOST = "0.0.0.0"
PORT = 5000

PONTOS_RECARGA = {
    "P1": ("ponto1", 6001),
    "P2": ("ponto2", 6002),
    "P3": ("ponto3", 6003)
}

def handle_client(client_socket, addr):
    logging.info(f"Cliente {addr} conectado.")

    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                logging.info(f"Cliente {addr} desconectou.")
                break

            mensagem = data.decode()
            veiculo = json.loads(mensagem)
            logging.info(f"Mensagem recebida do cliente: {veiculo} do tipo {type(veiculo)}")

            # Simula escolha do melhor ponto de recarga
            ponto_selecionado = "P1"
            #inserir a função para buscar o melhor ponto aqui
            
            ip_ponto, porta_ponto = PONTOS_RECARGA[ponto_selecionado]
            logging.info(f"Encaminhando para o ponto de recarga {ponto_selecionado} ({ip_ponto}:{porta_ponto})")

            # Comunicação com o ponto de recarga
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
                ponto_socket.connect((ip_ponto, porta_ponto))
                ponto_socket.sendall(mensagem.encode())
                resposta_ponto = ponto_socket.recv(1024)

            logging.info(f"Resposta do ponto de recarga: {resposta_ponto.decode()}")
            client_socket.sendall(resposta_ponto)

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
