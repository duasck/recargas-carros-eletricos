import socket
import threading

# Configuração do Servidor Central (Nuvem)
HOST = "0.0.0.0"  # Aceita conexões de qualquer IP
PORT = 5000       # Porta onde a nuvem escuta conexões dos clientes

# Lista de pontos de recarga disponíveis (serão definidos dinamicamente no Docker)
PONTOS_RECARGA = {
    "P1": ("ponto1", 6001),
    "P2": ("ponto2", 6002),
    "P3": ("ponto3", 6003)
}

def handle_client(client_socket, addr):
    """ Função que processa a requisição do cliente """
    print(f"[NUVEM] Cliente {addr} conectado.")

    while True:
        data = client_socket.recv(1024)  # Recebe a solicitação do cliente
        if not data:
            print(f"[NUVEM] Cliente {addr} desconectou.")
            break

        mensagem = data.decode()
        print(f"[NUVEM] Mensagem recebida do cliente: {mensagem}")

        # Simula escolha do melhor ponto de recarga
        ponto_selecionado = "P1"
        ip_ponto, porta_ponto = PONTOS_RECARGA[ponto_selecionado]

        # Encaminha a solicitação para o ponto de recarga
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as ponto_socket:
            ponto_socket.connect((ip_ponto, porta_ponto))
            ponto_socket.sendall(mensagem.encode())
            resposta_ponto = ponto_socket.recv(1024)

        client_socket.sendall(resposta_ponto)  # Envia resposta ao cliente

    client_socket.close()

# Inicia o servidor da nuvem
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

print(f"[NUVEM] Servidor rodando na porta {PORT}...")

while True:
    client_socket, addr = server_socket.accept()
    client_handler = threading.Thread(target=handle_client, args=(client_socket, addr))
    client_handler.start()
