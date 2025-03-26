import socket
import logging
import json

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [PONTO DE RECARGA] %(message)s")

HOST = "0.0.0.0"
PORT = 6001  # Modificável via Docker

class PontoRecarga:
    def __init__(self, id_ponto, localizacao):
        self.id_ponto = id_ponto
        self.localizacao = localizacao
        self.status = "disponivel"
        self.fila = []

    def reservar(self, id_veiculo):
        if self.status == "disponivel":
            self.status = "ocupado"
            self.fila.append(id_veiculo)
            return {"status": "reservado", "id_ponto": self.id_ponto}
        else:
            return {"status": "indisponivel"}

    def iniciar_recarga(self, taxa_recarga):
        if self.status == "ocupado":
            return {"status": "recarga_iniciada", "taxa_recarga": taxa_recarga}
        else:
            return {"status": "indisponivel"}

ponto = PontoRecarga(id_ponto="P1", localizacao={"lat": -23.5505, "lon": -46.6333})

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
            mensagem = json.loads(data.decode())
            logging.info(f"Mensagem recebida: {mensagem}")

            if mensagem["acao"] == "reservar":
                resposta = ponto.reservar(mensagem["id_veiculo"])
                conn.sendall(json.dumps(resposta).encode())
                logging.info(f"Reserva realizada: {resposta}")

            elif mensagem["acao"] == "iniciar_recarga":
                resposta = ponto.iniciar_recarga(mensagem["taxa_recarga"])
                conn.sendall(json.dumps(resposta).encode())
                logging.info(f"Recarga iniciada: {resposta}")

    except Exception as e:
        logging.error(f"Erro ao processar requisição: {e}")
    finally:
        conn.close()
        logging.info("Conexão encerrada.")