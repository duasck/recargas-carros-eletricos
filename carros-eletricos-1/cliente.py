import socket
import logging
import json
import os
import random
import argparse
from config import get_host

# Configuração do argparse para definir o modo de execução
parser = argparse.ArgumentParser()
parser.add_argument('--modo', type=int, default=0, help='0 - automatico 1 - manual')
args = parser.parse_args()

MODO_EXEC = args.modo

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CLIENTE-%(client_id)s] %(message)s"
)

# Configurações de conexão
TIMEOUT = 10
HOST_NUVEM = get_host("nuvem")
PORT_NUVEM = 5000

class Cliente:
    def __init__(self, id_veiculo, bateria, localizacao):
        self.id_veiculo = id_veiculo
        self.bateria = bateria
        self.localizacao = localizacao
        self.historico = []
        self.ponto_reservado = None

    def _enviar_mensagem(self, mensagem):
        """Método auxiliar para comunicação com a nuvem"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(TIMEOUT)
                client_socket.connect((HOST_NUVEM, PORT_NUVEM))
                client_socket.sendall(json.dumps(mensagem).encode())
                
                resposta = client_socket.recv(1024)
                return json.loads(resposta.decode())
                
        except socket.timeout:
            logging.error("Timeout na comunicação com a nuvem")
            return {"status": "erro", "mensagem": "Timeout"}
        except Exception as e:
            logging.error(f"Erro na comunicação: {e}")
            return {"status": "erro", "mensagem": str(e)}

    def listar_pontos_proximos(self):
        mensagem = {
            "acao": "listar_pontos",
            "id_veiculo": self.id_veiculo,
            "localizacao": self.localizacao
        }
        resposta = self._enviar_mensagem(mensagem)
        logging.info(f"Pontos próximos: {resposta}")
        return resposta if isinstance(resposta, list) else []

    def solicitar_reserva(self):
        mensagem = {
            "acao": "solicitar_reserva",
            "id_veiculo": self.id_veiculo,
            "localizacao": self.localizacao
        }
        resposta = self._enviar_mensagem(mensagem)
        
        if resposta.get("status") == "reservado":
            self.ponto_reservado = resposta.get("id_ponto")
        
        logging.info(f"Reserva: {resposta}")
        return resposta

    def liberar_ponto(self):
        if not self.ponto_reservado:
            return {"status": "nenhum_ponto_reservado"}

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((HOST_NUVEM, PORT_NUVEM))
                
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
                client_socket.connect((HOST_NUVEM, PORT_NUVEM))
                
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

def menu():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        opcao = input('''Digite uma ação para o cliente:
    1 - Solicitar pontos próximos
    2 - Solicitar reserva
    3 - Solicitar histórico
    4 - Liberar ponto
    5 - Sair\n >>> ''')
        if opcao == '1':
            cliente.listar_pontos_proximos()
        elif opcao == '2':
            cliente.solicitar_reserva()
        elif opcao == '3':
            cliente.solicitar_historico()
        elif opcao == '4':
            cliente.liberar_ponto()
        elif opcao == '5':
            break 
        else:
            print("Escolha uma opção válida (1 a 5)!")
        input('Pressione enter...')

def automatico():
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

if __name__ == '__main__':
    if MODO_EXEC == 1:
        menu()
    else:  # 0 para automático
        automatico()