import socket
import logging
import json
import os

# Configuração do logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [CLIENTE] %(message)s")

HOST = "nuvem"  # Nome do serviço da nuvem no Docker
PORT = 5000     # Porta da Nuvem

class Cliente:
    def __init__(self, id_veiculo, bateria, localizacao):
        self.id_veiculo = id_veiculo
        self.bateria = bateria
        self.localizacao = localizacao
        self.historico = []

    def listar_pontos_proximos(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            logging.info("Conectado à Nuvem.")

            mensagem = {
                "acao": "listar_pontos",
                "id_veiculo": self.id_veiculo,
                "bateria": self.bateria,
                "localizacao": self.localizacao
            }
            
            # enviando os dados
            client_socket.sendall(json.dumps(mensagem).encode())

            # recebe os dados
            resposta = client_socket.recv(1024)
            pontos_proximos = json.loads(resposta.decode())
            
            logging.info(f"Pontos de recarga próximos: {pontos_proximos}")
            return pontos_proximos

        except Exception as e:
            logging.error(f"Erro no cliente: {e}")
        finally:
            client_socket.close()
            logging.info("Conexão encerrada.")

    def solicitar_reserva(self, id_posto, taxa_pagamento):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            logging.info("Conectado à Nuvem.")

            mensagem = {
                "acao": "solicitar_reserva",
                "id_veiculo": self.id_veiculo,
                "id_posto": id_posto,
                "taxa_pagamento": taxa_pagamento
            }
            
            client_socket.sendall(json.dumps(mensagem).encode())

            resposta = client_socket.recv(1024)
            status_reserva = json.loads(resposta.decode())
            logging.info(f"Status da reserva: {status_reserva}")
            return status_reserva

        except Exception as e:
            logging.error(f"Erro no cliente: {e}")
        finally:
            client_socket.close()
            logging.info("Conexão encerrada.")

    def solicitar_historico(self):
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((HOST, PORT))
            logging.info("Conectado à Nuvem.")

            mensagem = {
                "acao": "solicitar_historico",
                "id_veiculo": self.id_veiculo
            }
            client_socket.sendall(json.dumps(mensagem).encode())

            resposta = client_socket.recv(1024)
            historico = json.loads(resposta.decode())
            logging.info(f"Histórico de pagamentos: {historico}")
            return historico

        except Exception as e:
            logging.error(f"Erro no cliente: {e}")
        finally:
            client_socket.close()
            logging.info("Conexão encerrada.")

# Exemplo de uso

cliente = Cliente(id_veiculo="ABC123", bateria=20, localizacao={"lat": -23.5505, "lon": -46.6333})
while True:
    os.system('clear')
    option = input('''Digite uma opção:
          1 - Listar pontos proximos
          2 - Solicitar reserva
          3 - Solicitar histório
          >>> ''')
    if option == '1':
        pontos_proximos = cliente.listar_pontos_proximos()
    elif option == '2':
        status_reserva = cliente.solicitar_reserva(id_posto="P1", taxa_pagamento=50.0)
    elif option == '3':
        historico = cliente.solicitar_historico()
    else: 
        # print("Digite uma opção válida!!")
        print("Digite uma opção válida!!!")
    input("Pressione enter para continuar")