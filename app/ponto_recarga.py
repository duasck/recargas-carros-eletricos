import socket
import logging

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [PONTO DE RECARGA] %(message)s")

HOST = "0.0.0.0"
PORT = 6001  # Modificável via Docker

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

logging.info(f"Servidor do Ponto de Recarga rodando na porta {PORT}...")

while True:
    conn, addr = s.accept()
    logging.info(f"Conexão recebida de {addr}")

    try:
        data = conn.recv(1024)
        if data:
            mensagem = data.decode()
            logging.info(f"Mensagem recebida: {mensagem}")
            resposta = "Recarga iniciada com sucesso!"
            conn.sendall(resposta.encode())
            logging.info("Resposta enviada ao cliente.")

    except Exception as e:
        logging.error(f"Erro ao processar requisição: {e}")

    finally:
        conn.close()
        logging.info("Conexão encerrada.")
