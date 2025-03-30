import socket
import logging
import json
import os
from random import uniform

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(container_id)s] %(message)s"
)

HOST = "0.0.0.0"
BASE_PORT = int(os.getenv('BASE_PORT', 6000))

# Obtém o ID do container a partir do hostname
container_id = os.getenv('HOSTNAME', 'ponto_1').split('_')[-1]
PORT = BASE_PORT + int(container_id)

class PontoRecarga:
    def __init__(self, id_ponto, localizacao):
        self.id_ponto = id_ponto
        self.localizacao = localizacao
        self.status = "disponivel"
        self.fila = []
        self.veiculo_atual = None

    def reservar(self, id_veiculo):
        if self.status == "disponivel":
            self.status = "reservado"
            self.veiculo_atual = id_veiculo
            return {
                "status": "reservado",
                "id_ponto": self.id_ponto,
                "localizacao": self.localizacao
            }
        else:
            return {"status": "indisponivel"}

    def iniciar_recarga(self, taxa_recarga):
        if self.status == "reservado" and self.veiculo_atual:
            self.status = "ocupado"
            return {
                "status": "recarga_iniciada",
                "taxa_recarga": taxa_recarga,
                "id_ponto": self.id_ponto
            }
        else:
            return {"status": "indisponivel"}

    def liberar(self):
        if self.status in ["reservado", "ocupado"]:
            self.status = "disponivel"
            self.veiculo_atual = None
            return {"status": "liberado"}
        return {"status": "já_disponivel"}

# Configuração do ponto de recarga
ponto = PontoRecarga(
    id_ponto=f"P{container_id}",
    localizacao={
        "lat": -23.5505 + (int(container_id) * 0.01),
        "lon": -46.6333 + (int(container_id) * 0.01)
    }
)

# Adiciona container_id a todos os logs
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.container_id = f"PONTO-{container_id}"
    return record
logging.setLogRecordFactory(record_factory)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

logging.info(f"Servidor do Ponto de Recarga {ponto.id_ponto} rodando na porta {PORT}...")
logging.info(f"Localização: {ponto.localizacao}")

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
                resposta = ponto.iniciar_recarga(mensagem.get("taxa_recarga", 10.0))
                conn.sendall(json.dumps(resposta).encode())
                logging.info(f"Recarga iniciada: {resposta}")

            elif mensagem["acao"] == "liberar":
                resposta = ponto.liberar()
                conn.sendall(json.dumps(resposta).encode())
                logging.info(f"Ponto liberado: {resposta}")

    except Exception as e:
        logging.error(f"Erro ao processar requisição: {e}")
    finally:
        conn.close()
        logging.info("Conexão encerrada.")