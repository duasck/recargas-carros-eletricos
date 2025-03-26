import pygame
import random
from cliente import Cliente  # Importa a classe Cliente do cliente.py

# Função para gerar coordenadas aleatórias nas ruas
def geraCoordenadas(ruas):
    return random.choice(ruas)

# Função para definir o movimento do veículo
def anda(direcao_atual):
    opcoes = {
        "cima": [(0, -1), (1, 0), (-1, 0)],
        "baixo": [(0, 1), (1, 0), (-1, 0)],
        "esquerda": [(-1, 0), (0, -1), (0, 1)],
        "direita": [(1, 0), (0, -1), (0, 1)]
    }
    return random.choices(opcoes[direcao_atual], weights=[0.8, 0.1, 0.1])[0]

# Função para definir a direção do veículo com base no movimento
def definir_direcao(direcao_atual, movimento):
    if movimento == (0, -1):
        return "cima"
    elif movimento == (0, 1):
        return "baixo"
    elif movimento == (-1, 0):
        return "esquerda"
    elif movimento == (1, 0):
        return "direita"
    return direcao_atual

# Função para criar o mapa com ruas e pontos de recarga
def criar_mapa(tamanho):
    mapa = [[0 for _ in range(tamanho)] for _ in range(tamanho)]
    ruas = []
    
    for i in range(0, tamanho, 10):
        for j in range(tamanho):
            mapa[i][j] = 1
            ruas.append((i, j))
    for i in range(0, tamanho, 15):
        for j in range(tamanho):
            mapa[j][i] = 1
            ruas.append((j, i))
    
    pontos_recarga = random.sample(ruas, 5)
    return mapa, ruas, pontos_recarga

# Função principal do veículo
def veiculo():
    pygame.init()
    tamanho = 100
    tamanho_celula = 4
    largura, altura = 640, 480
    tela = pygame.display.set_mode((largura, altura))
    pygame.display.set_caption("Simulação do Veículo")
    
    mapa, ruas, pontos_recarga = criar_mapa(tamanho)
    cordX, cordY = geraCoordenadas(ruas)
    bateria = 100
    direcao_atual = "direita"
    cor_fundo = (50, 50, 50)
    cor_veiculo = (0, 255, 0)
    cor_rua = (200, 200, 200)
    cor_recarga = (255, 0, 0)
    
    # Cria uma instância do cliente (veículo)
    cliente = Cliente(id_veiculo="ABC123", bateria=bateria, localizacao={"lat": cordX, "lon": cordY})
    
    rodando = True
    while rodando and bateria > 20:
        pygame.time.delay(100)
        tela.fill(cor_fundo)
        
        # Desenha as ruas
        for x, y in ruas:
            pygame.draw.rect(tela, cor_rua, (x * tamanho_celula, y * tamanho_celula, tamanho_celula, tamanho_celula))
        
        # Desenha os pontos de recarga
        for x, y in pontos_recarga:
            pygame.draw.rect(tela, cor_recarga, (x * tamanho_celula, y * tamanho_celula, tamanho_celula * 3, tamanho_celula * 3))
        
        # Movimentação do veículo
        if random.random() > 0.2:
            movimento = anda(direcao_atual)
            novo_x, novo_y = cordX + movimento[0], cordY + movimento[1]
            
            # Verifica se o novo movimento está dentro dos limites do mapa e nas ruas
            if (novo_x, novo_y) in ruas and 0 <= novo_x < tamanho and 0 <= novo_y < tamanho:
                cordX, cordY = novo_x, novo_y
                bateria -= 1
                direcao_atual = definir_direcao(direcao_atual, movimento)
        
        # Desenha o veículo
        pygame.draw.rect(tela, cor_veiculo, (cordX * tamanho_celula, cordY * tamanho_celula, tamanho_celula * 3, tamanho_celula * 3))
        pygame.display.update()
        
        # Verifica se o veículo está próximo de um ponto de recarga
        if (cordX, cordY) in pontos_recarga:
            logging.info("Veículo próximo a um ponto de recarga.")
            # Solicita uma reserva no ponto de recarga
            status_reserva = cliente.solicitar_reserva(id_posto="P1", taxa_pagamento=50.0)
            if status_reserva["status"] == "reservado":
                logging.info("Reserva realizada. Iniciando recarga...")
                bateria = 100  # Recarrega a bateria
                logging.info("Bateria recarregada.")
        
        # Verifica eventos do Pygame (fechar janela)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando = False
    
    pygame.quit()

# Executa a simulação do veículo
veiculo()