import socket
import logging
import json
import os
import random
from random_info import listaClientes

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLIENTE-%(client_id)s] %(message)s"
)

HOST = "nuvem"
PORT = 5000

class Cliente:
    def __init__(self, id_veiculo, bateria, localizacao):
        self.id_veiculo = id_veiculo
        self.bateria = bateria
        self.localizacao = localizacao
        self.historico = []
        self.ponto_reservado = None

    def listar_pontos_proximos(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST, PORT))
                
                mensagem = {
                    "acao": "listar_pontos",
                    "id_veiculo": self.id_veiculo,
                    "localizacao": self.localizacao
                }
                
                client_socket.sendall(json.dumps(mensagem).encode())
                resposta = client_socket.recv(1024)
                pontos_proximos = json.loads(resposta.decode())
                
                logging.info(f"Pontos próximos: {pontos_proximos}")
                return pontos_proximos

        except Exception as e:
            logging.error(f"Erro ao listar pontos: {e}")
            return []

    def solicitar_reserva(self):
        pontos = self.listar_pontos_proximos()
        if not pontos:
            return {"status": "nenhum_ponto_disponivel"}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST, PORT))
                
                mensagem = {
                    "acao": "solicitar_reserva",
                    "id_veiculo": self.id_veiculo,
                    "localizacao": self.localizacao
                }
                
                client_socket.sendall(json.dumps(mensagem).encode())
                resposta = client_socket.recv(1024)
                status_reserva = json.loads(resposta.decode())
                
                if status_reserva.get("status") == "reservado":
                    self.ponto_reservado = status_reserva.get("id_ponto")
                
                logging.info(f"Reserva: {status_reserva}")
                return status_reserva

        except Exception as e:
            logging.error(f"Erro ao solicitar reserva: {e}")
            return {"status": "erro", "mensagem": str(e)}

    def liberar_ponto(self):
        if not self.ponto_reservado:
            return {"status": "nenhum_ponto_reservado"}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST, PORT))
                
                mensagem = {
                    "acao": "liberar_ponto",
                    "id_ponto": self.ponto_reservado,
                    "id_veiculo": self.id_veiculo
                }
                
                client_socket.sendall(json.dumps(mensagem).encode())
                resposta = client_socket.recv(1024)
                status = json.loads(resposta.decode())
                
                if status.get("status") == "liberado":
                    self.ponto_reservado = None
                
                logging.info(f"Liberação: {status}")
                return status

        except Exception as e:
            logging.error(f"Erro ao liberar ponto: {e}")
            return {"status": "erro", "mensagem": str(e)}

    def solicitar_historico(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST, PORT))
                
                mensagem = {
                    "acao": "solicitar_historico",
                    "id_veiculo": self.id_veiculo
                }
                
                client_socket.sendall(json.dumps(mensagem).encode())
                resposta = client_socket.recv(1024)
                historico = json.loads(resposta.decode())
                
                logging.info(f"Histórico: {historico}")
                return historico

        except Exception as e:
            logging.error(f"Erro ao solicitar histórico: {e}")
            return []

# Configuração do logging com client_id
client_id = os.getenv('HOSTNAME', 'cliente_1').split('_')[-1]
old_factory = logging.getLogRecordFactory()

def record_factory(*args, **kwargs):
    record = old_factory(*args, **kwargs)
    record.client_id = client_id
    return record

logging.setLogRecordFactory(record_factory)

# Seleciona um cliente aleatório ou usa um padrão
try:
    cliente_info = random.choice(listaClientes)
except IndexError:
    cliente_info = type('', (), {'id': f'cliente_{client_id}', 'coordenadas': [random.uniform(-23.56, -23.54), random.uniform(-46.66, -46.62)]})()

cliente = Cliente(
    id_veiculo=cliente_info.id,
    bateria=random.randint(10, 30),
    localizacao={
        "lat": cliente_info.coordenadas[0],
        "lon": cliente_info.coordenadas[1]
    }
)

# Simulação de comportamento do cliente
import time

while True:
    try:
        # Lista pontos próximos
        cliente.listar_pontos_proximos()
        time.sleep(1)
        
        # Tenta fazer uma reserva
        if random.random() > 0.3:  # 70% de chance de tentar reservar
            cliente.solicitar_reserva()
            time.sleep(2)
            
            # Libera o ponto após um tempo
            if cliente.ponto_reservado and random.random() > 0.5:
                time.sleep(3)
                cliente.liberar_ponto()
        
        # Consulta histórico ocasionalmente
        if random.random() > 0.8:  # 20% de chance
            cliente.solicitar_historico()
        
        time.sleep(random.randint(2, 5))
        
    except KeyboardInterrupt:
        if cliente.ponto_reservado:
            cliente.liberar_ponto()
        break
    except Exception as e:
        logging.error(f"Erro no loop principal: {e}")
        time.sleep(5)