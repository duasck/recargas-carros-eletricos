
# Sistema Distribuído de Recarga de Veículos Elétricos com Blockchain

Este projeto simula um ecossistema descentralizado para recarga de veículos elétricos (VEs). A arquitetura é distribuída, sem um ponto central de falha, e utiliza tecnologias como MQTT para comunicação em tempo real, APIs REST (Flask) para coordenação entre servidores, e um blockchain Ethereum para garantir a segurança, transparência e auditabilidade de todas as transações (reservas, recargas e pagamentos).

[![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-black?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)
[![MQTT](https://img.shields.io/badge/MQTT-Broker-brightgreen?style=for-the-badge&logo=mqtt)](https://mqtt.org/)
[![Ethereum](https://img.shields.io/badge/Ethereum-Solidity-lightgrey?style=for-the-badge&logo=ethereum)](https://ethereum.org/)

##  arquitetura

O sistema é composto por múltiplos servidores autônomos (representando diferentes empresas de recarga), veículos elétricos (clientes) e um ledger distribuído (blockchain). A comunicação e coordenação ocorrem da seguinte forma:

```mermaid
graph TD
    subgraph "Clientes"
        Car1[🚗 Carro 1]
        Car2[🚗 Carro 2]
    end

    subgraph "Infraestrutura de Comunicação"
        Broker[📡 Broker MQTT]
    end

    subgraph "Servidores das Empresas (Pares)"
        ServerA[🏢 Servidor A (Flask API)]
        ServerB[🏢 Servidor B (Flask API)]
        ServerC[🏢 Servidor C (Flask API)]
    end

    subgraph "Ledger Distribuído"
        Geth[🔗 Nó Geth (Ethereum)]
        Contract[📜 Contrato Inteligente]
        API[📊 API de Transações]
    end

    Car1 -- 1. Planejamento de Rota (MQTT) --> Broker
    Broker -- 2. Encaminha Requisição --> ServerA
    ServerA -- 3. Coordena Reservas (HTTP API) --> ServerB
    ServerB -- 4. Responde Preparação --> ServerA
    ServerA -- 5. Envia Plano de Rota (MQTT) --> Broker
    Broker -- 6. Notifica Carro --> Car1

    Car1 -- Durante a Viagem --> Broker
    Broker -- Notificações de Recarga --> ServerA
    ServerA -- Registra Transações --> Geth
    Geth -- Armazena no --> Contract

    API -- Consulta Dados --> Contract
```

### Componentes Principais

-   **`car.py`**: Simula um veículo elétrico. Ele planeja rotas, "viaja" entre cidades, consome bateria, solicita recargas e realiza pagamentos. Cada ação crítica é assinada digitalmente com sua chave privada.
-   **`generic_server.py`**: Contém a lógica de negócio principal de um servidor de empresa. Gerencia pontos de recarga, filas, e implementa um protocolo de confirmação em duas fases (2PC) para reservas inter-servidores.
-   **`servers/server_*.py`**: Configurações específicas para cada empresa/servidor (ex: `server_a.py` para a Bahia), definindo seus pontos de recarga e portas.
-   **`blockchain/`**:
    -   **`contract.sol`**: O contrato inteligente que gerencia identidades, saldos e o registro imutável de transações.
    -   **`deploy_contract.py`**: Script que compila e implanta o contrato na rede Geth.
    -   **`ledger.py`**: Abstração em Python para interagir com o contrato (registrar transações, etc.).
-   **`transactions.py`**: Uma API REST para consultar publicamente o histórico de transações e saldos registrados no blockchain.
-   **`generate_compose.py`**: Script utilitário para gerar os arquivos `docker-compose.yml` dinamicamente.
-   **`generate_keys.py`**: Script para gerar os pares de chaves (pública/privada) para todos os participantes da simulação.

## Funcionalidades

-   ✅ **Arquitetura 100% Descentralizada**: Sem servidor central de controle.
-   🔒 **Comunicação Segura**: Todas as requisições de veículos são assinadas com ECDSA para garantir autenticidade e integridade.
-   🤝 **Reservas Coordenadas**: Implementação de um protocolo de consenso (similar ao 2PC) para garantir que uma rota longa com múltiplas paradas de recarga seja totalmente reservada antes do início da viagem.
-   🔗 **Integração com Blockchain**: Todas as transações (reservas, recargas, pagamentos) são registradas em um ledger Ethereum imutável e auditável.
-   💸 **Contabilidade On-Chain**: Saldos de veículos e empresas são gerenciados diretamente pelo contrato inteligente.
-   📊 **API de Transparência**: Um endpoint público permite a qualquer um visualizar o histórico de transações do sistema.

## Pré-requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados:
-   [Python](https://www.python.org/downloads/) (versão 3.9 ou superior)
-   [Docker](https://www.docker.com/get-started)
-   [Docker Compose](https://docs.docker.com/compose/install/)
-   [Git](https://git-scm.com/)

## 🚀 Guia de Execução

Siga os passos abaixo para configurar e executar a simulação completa.

### Passo 1: Clonar o Repositório

```sh
git clone <url-do-seu-repositorio>
cd recargas-carros-eletricos
```

### Passo 2: Instalar Dependências

É uma boa prática usar um ambiente virtual.

```sh
# Criar e ativar ambiente virtual (opcional, mas recomendado)
python -m venv venv
source venv/bin/activate  # No Linux/macOS
# venv\Scripts\activate   # No Windows

# Instalar as bibliotecas Python
pip install -r requirements.txt
```

### Passo 3: Gerar Chaves e Arquivos de Configuração

O sistema precisa de chaves criptográficas para todos os participantes e de arquivos `docker-compose` para orquestração.

1.  **Gere as chaves:**
    Este comando criará o arquivo `keys.json` com chaves para as empresas, veículos e o implantador do contrato.
    ```sh
    python generate_keys.py
    ```

2.  **Gere os arquivos do Docker Compose:**
    Este comando cria `docker-compose.servers.yml` e `docker-compose.cars.yml`. Você pode especificar o número de carros.
    ```sh
    # Gera a configuração para 5 carros (valor padrão)
    python generate_compose.py 5
    ```

### Passo 4: Executar a Simulação com Docker Compose (Recomendado)

Esta é a maneira mais fácil de rodar o ecossistema completo.

1.  **Inicie a infraestrutura (Servidores, Blockchain, etc.):**
    Abra um terminal e execute o seguinte comando. O `--build` garante que a imagem será construída. O `-d` executa em modo "detached" (em segundo plano).

    ```sh
    docker compose -f docker-compose.servers.yml up --build -d
    ```
    Este comando irá:
    -   Construir a imagem Docker do projeto.
    -   Iniciar um nó Geth (Ethereum).
    -   Iniciar o contêiner `contract_deploy` para implantar o contrato inteligente no nó Geth.
    -   Iniciar os 5 servidores de recarga (A, B, C, D, E).
    -   Iniciar a API de transações.

2.  **Inicie os Carros:**
    Em outro terminal (ou no mesmo), inicie os contêineres dos carros.

    ```sh
    docker compose -f docker-compose.cars.yml up --build
    ```
    Agora você verá os logs dos carros em tempo real, mostrando o planejamento da rota, as viagens, as recargas e os pagamentos.

3.  **Monitorando a Simulação:**
    Para ver o log de um componente específico (ex: `car_1` ou `server_a`):
    ```sh
    docker compose -f docker-compose.cars.yml logs -f car_1
    docker compose -f docker-compose.servers.yml logs -f server_a
    ```

4.  **Encerrando a Simulação:**
    Quando terminar, pressione `Ctrl+C` no terminal dos carros e depois execute o seguinte comando para parar e remover todos os contêineres e redes:
    ```sh
    docker compose -f docker-compose.servers.yml down
    docker compose -f docker-compose.cars.yml down
    ```

## 🔍 Visualizando Transações no Blockchain

A API de transparência roda na porta `5100` do seu Docker host. Você pode usar `curl` ou um navegador para consultar os dados.

-   **Listar todas as transações registradas:**
    ```sh
    curl http://localhost:5100/api/transactions | python -m json.tool
    ```

-   **Consultar o saldo de uma conta específica (ex: da empresa 'company_a'):**
    Primeiro, pegue o endereço da `company_a` do arquivo `keys.json`. Em seguida, use-o no comando:
    ```sh
    # Exemplo de endereço: 0xDc429D726965f9790028E5628ce6d39BB070BBCc
    curl http://localhost:5100/api/balance/0xDc429D726965f9790028E5628ce6d39BB070BBCc
    ```

## 📁 Estrutura do Projeto

```
.
├── blockchain/
│   ├── contract.sol            # Contrato inteligente
│   ├── deploy_contract.py      # Script de implantação do contrato
│   └── ledger.py               # Módulo de interação com o blockchain
├── servers/
│   ├── server_a.py             # Configuração do Servidor A
│   ├── ...                     # Outros servidores
│   └── server_e.py
├── car.py                      # Lógica do simulador de veículo elétrico
├── constants.py                # Constantes globais (portas, cidades, etc.)
├── generic_server.py           # Lógica genérica compartilhada pelos servidores
├── generate_compose.py         # Gerador de arquivos docker-compose
├── generate_keys.py            # Gerador de chaves criptográficas
├── keys.json                   # Chaves públicas/privadas (gerado)
├── transactions.py             # API pública para consulta de transações
├── Dockerfile                  # Define a imagem Docker para os serviços
├── requirements.txt            # Dependências Python
└── README.md                   # Este arquivo
```