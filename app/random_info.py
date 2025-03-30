import random
import os

class Cliente:
    def __init__(self, id, coordenadas):
        self.id = id
        self.coordenadas = coordenadas


# Função para gerar coordenadas aleatórias nas ruas
def geraCoordenadas():
    return (random.randint(0, 100), random.randint(0, 100))


# Função principal do veículo
def veiculo():
    pass


listaClientes = []
listaPontos = []
PORTAINICIAL = 6000

while True:
    os.system('cls' if os.name == 'nt' else 'clear')
    opcao = input("""O que quer gerar?\n
    1-Clientes
    2-Pontos de recarga
    3-Sair
    >>>\n""")

    if opcao == "1":
        # Gera um cliente com coordenadas aleatórias
        nCLientes = input ("Quantos clientes quer gerar?")
        for i in range(int(nCLientes)):
            id = ("Cliente" + str(i))
            coordenadas = geraCoordenadas()
            cliente = Cliente(id, coordenadas)
            listaClientes.append(cliente)

    elif opcao == "2":
        # Gera um ponto de recarga com coordenadas aleatórias
        nPontos = input ("Quantos pontos de recarga quer gerar?")
        for i in range(int(nPontos)):
            portaPonto = PORTAINICIAL + i
            coordenadas = geraCoordenadas()

    elif opcao == "3":
        # Sair do programa
        break
    
    else:
        input("Opção inválida. Tente novamente.")

    input("Pressione Enter para continuar.")


    
        