import socket

HOST = "nuvem"  # Nome do serviço da nuvem no Docker
PORT = 5000      # Porta da Nuvem

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

mensagem = "Solicitação de recarga - Veículo ABC123"
client_socket.sendall(mensagem.encode())

resposta = client_socket.recv(1024)
print("Resposta da Nuvem:", resposta.decode())

client_socket.close()
