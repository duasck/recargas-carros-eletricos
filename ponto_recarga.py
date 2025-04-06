import socket
import logging
import json
import os
import time
from random import uniform

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(container_id)s] %(message)s"
)

HOST = "0.0.0.0"
# Obtém o ID do ponto da variável de ambiente
PONTO_ID = os.getenv('PONTO_ID', '1')
PORT = int(os.getenv('PORT', 6001))  # Porta definida pelo compose ou porta padrão

class PontoRecarga:
    def __init__(self, id_ponto, localizacao):
        self.id_ponto = f"P{PONTO_ID}"  # Usa o ID definido no compose
        self.localizacao = localizacao
        self.status = "disponivel"
        self.veiculo_atual = None
        self.nivel_bateria = 20  # Bateria inicial do veículo em kWh
        self.capacidade_maxima = 100  # Capacidade máxima do veículo

    def reservar(self, id_veiculo):
        if self.status == "disponivel":
            self.status = "reservado"
            self.veiculo_atual = id_veiculo
            return {
                "status": "reservado",
                "id_ponto": self.id_ponto,
                "localizacao": self.localizacao,
                "bateria_atual": self.nivel_bateria
            }
        else:
            return {"status": "indisponivel"}

    def iniciar_recarga(self, taxa_recarga):
        import datetime

        if self.status == "reservado" and self.veiculo_atual:
            self.status = "ocupado"

            valor_kwh = float(input("Quantos kWh deseja carregar?\n >>> "))
            forma_pagamento = input("Forma de pagamento (1 - cartão crédito ou debito\n2 - pix):\n >>> ")

            capacidade_restante = self.capacidade_maxima - self.nivel_bateria
            recarga_real = min(valor_kwh, capacidade_restante)

            print(f"\n🔌 Iniciando recarga de {recarga_real} kWh...")
            for i in range(int(recarga_real)):
                time.sleep(1)  # Simula 1 segundo por kWh
                self.nivel_bateria += 1
                print(f"⚡ {i+1} kWh carregados - Bateria: {self.nivel_bateria}/{self.capacidade_maxima} kWh")

            print("✅ Recarga finalizada.")

            return {
                "status": "recarga_finalizada",
                "taxa_recarga": taxa_recarga,
                "id_ponto": self.id_ponto,
                "id_veiculo": self.veiculo_atual,
                "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "forma_pagamento": "cartão" if forma_pagamento == "1" else "pix",
                "valor": recarga_real,
                "bateria_final": self.nivel_bateria,
                "tempo_total": f"{int(recarga_real)} segundos"
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
    id_ponto=PONTO_ID,
    localizacao={
        # Gera localização baseada no ID do ponto para distribuição consistente
        "lat": -23.5505 + (int(PONTO_ID) * 0.001),
        "lon": -46.6333 + (int(PONTO_ID) * 0.001)
    }
)

# Configuração do logging
old_factory = logging.getLogRecordFactory()
def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.container_id = f"PONTO-{PONTO_ID}"
    return record
logging.setLogRecordFactory(record_factory)

# Configuração do socket
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

            elif mensagem["acao"] == "status_recarga":
                status = "finalizada" if not self.recarga_em_andamento else "em andamento"
                conn.sendall(json.dumps({"status": status}).encode())
            
            elif mensagem["acao"] == "liberar":
                resposta = ponto.liberar()
                conn.sendall(json.dumps(resposta).encode())
                logging.info(f"Ponto liberado: {resposta}")

    except Exception as e:
        logging.error(f"Erro ao processar requisição: {e}")
    finally:
        conn.close()
        logging.info("Conexão encerrada.")