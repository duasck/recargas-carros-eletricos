#!/usr/bin/env python3 
import random
import os
import json


class Cliente:
    def __init__(self, id, coordenadas):
        self.id = id
        self.coordenadas = coordenadas

class PontoRecarga:
    def __init__(self, id, porta, coordenadas, status):
        self.id = id
        self.porta = porta
        self.coordenadas = coordenadas
        self.status = status 

def geraCoordenadas():
    return (random.uniform(-23.56, -23.54), random.uniform(-46.66, -46.62))

listaClientes = []
listaPontos = []

def gerar_clientes(n):
    global listaClientes
    listaClientes = []
    for i in range(1, n + 1):
        cliente = Cliente(
            id=f"cliente_{i}",
            coordenadas=geraCoordenadas()
        )
        listaClientes.append(cliente)
    print(f"{n} clientes gerados com sucesso!")

def gerar_pontos(n):
    global listaPontos
    listaPontos = []
    for i in range(1, n + 1):
        ponto = PontoRecarga(
            id=f"P{i}",
            porta=6000 + i,
            coordenadas=geraCoordenadas(),
            status="disponivel"
        )
        listaPontos.append(ponto)
    print(f"{n} pontos de recarga gerados com sucesso!")
    print(listaPontos)

def salvar_dados():
    try: 
        with open('dados_clientes.json', 'w') as f:
            json.dump([{'id': cliente.id, 'coordenadas': cliente.coordenadas} for cliente in listaClientes], f)

        with open('dados_pontos.json', 'w') as f:
            json.dump([{'id': ponto.id, 'porta': ponto.porta, 'coordenadas': ponto.coordenadas, 'status': ponto.status} for ponto in listaPontos], f)
    except Exception as e:
        print(f"Não foi possível salvar os dados: {e}")
        
def carregar_dados():
    global listaClientes, listaPontos
    
    # Verifica e carrega clientes
    try:
        if os.path.getsize('./dados_clientes.json') > 0:  # Verifica se o arquivo não está vazio
            with open('./dados_clientes.json', 'r') as f:
                dados = json.load(f)
                listaClientes = [Cliente(cliente['id'], cliente['coordenadas']) for cliente in dados]
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # Ignora erro se o arquivo não existir ou estiver corrompido
    
    # Verifica e carrega pontos de recarga
    try:
        if os.path.getsize('./dados_pontos.json') > 0:  # Verifica se o arquivo não está vazio
            with open('./dados_pontos.json', 'r') as f:
                dados = json.load(f)
                listaPontos = [PontoRecarga(ponto['id'], ponto['porta'], ponto['coordenadas'], ponto['status']) for ponto in dados]
    except (FileNotFoundError, json.JSONDecodeError):
        pass  # Ignora erro se o arquivo não existir ou estiver corrompido

def menu():
    carregar_dados()
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"""Clientes: {len(listaClientes)} | Pontos: {len(listaPontos)}
        
Opções:
1 - Gerar clientes
2 - Gerar pontos de recarga
3 - Visualizar dados
4 - Salvar dados
5 - Sair
        """)
        
        opcao = input("Escolha uma opção: ")
        
        if opcao == "1":
            n = int(input("Quantos clientes deseja gerar? "))
            gerar_clientes(n)
            salvar_dados()
        elif opcao == "2":
            n = int(input("Quantos pontos de recarga deseja gerar? "))
            gerar_pontos(n)
            salvar_dados()
        elif opcao == "3":
            print("\nClientes:")
            for cliente in listaClientes[:5]:  # Mostra apenas os 5 primeiros
                print(f"  {cliente.id}: {cliente.coordenadas}")
            
            print("\nPontos de recarga:")
            for ponto in listaPontos[:5]:  # Mostra apenas os 5 primeiros
                print(f"  {ponto.id}: Porta {ponto.porta}, Local: {ponto.coordenadas}, status: {ponto.status}")
        elif opcao == "4":
            salvar_dados()
            print("Dados salvos com sucesso!")
        elif opcao == "5":
            break
        else:
            print("Opção inválida!")
        
        input("\nPressione Enter para continuar...")

if __name__ == "__main__":
    menu()

