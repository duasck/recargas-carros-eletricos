import socket

# Configuração do Ponto de Recarga
HOST = "0.0.0.0"   # Aceita conexões da nuvem
PORT = 6001        # Porta do ponto de recarga (será parametrizada no Docker)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
s.listen()

print(f"[PONTO DE RECARGA] Servidor rodando na porta {PORT}...")

while True:
    conn, addr = s.accept()
    print(f"[PONTO DE RECARGA] Conexão recebida de {addr}")

    data = conn.recv(1024)
    if not data:
        break

    print(f"[PONTO DE RECARGA] Mensagem recebida: {data.decode()}")
    conn.sendall(b"Recarga iniciada com sucesso!")

    conn.close()
