# Recargas Carros Elétricos

Este projeto simula um sistema distribuído de recarga de carros elétricos, com múltiplos servidores e clientes (carros), utilizando Flask, MQTT, Docker e blockchain Ethereum.

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação Local](#instalação-local)
- [Execução com Docker Compose](#execução-com-docker-compose)
- [Execução Distribuída](#execução-distribuída-2-computadores)
- [Gerando arquivos docker-compose](#gerando-arquivos-docker-compose-automaticamente)
- [Como encontrar o IP do container](#como-encontrar-o-ip-do-container-docker-dos-servidores)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Integração Blockchain](#integração-blockchain)
- [Pagamentos e Contabilidade](#pagamentos-e-contabilidade)
- [Visualização de Transações](#visualização-de-transações)

## Pré-requisitos

- Python 3.9+
- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/)
- Broker MQTT acessível (`broker.hivemq.com` por padrão)
- Node.js (para compilar contratos Solidity)

## Instalação Local

1. **Clone o repositório:**
   ```sh
   git clone <url-do-repositorio>
   cd recargas-carros-eletricos
   ```

2. **Crie um ambiente virtual:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Instale as dependências:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Execute um servidor (exemplo: server_a):**
   ```sh
   python servers/server_a.py
   ```

5. **Execute um carro:**
   ```sh
   MQTT_BROKER=broker.hivemq.com VEHICLE_ID=car1 VEHICLE_PRIVATE_KEY=0xYourPrivateKey python car.py
   ```

## Execução com Docker Compose

1. **Gere os arquivos de compose:**
   ```sh
   python generate_compose.py 5
   ```
   Gera `docker-compose.servers.yml` e `docker-compose.cars.yml` (5 carros).

2. **Suba os servidores:**
   ```sh
   docker compose -f docker-compose.servers.yml up --build
   ```

3. **Suba os carros:**
   ```sh
   docker compose -f docker-compose.cars.yml up --build
   ```

## Execução Distribuída (2 computadores)

### Computador 1: Servidores
1. Gere e suba os servidores:
   ```sh
   python generate_compose.py
   docker compose -f docker-compose.servers.yml up --build
   ```
2. Descubra o IP (ex: `192.168.1.10`).

### Computador 2: Carros
1. Copie o projeto.
2. Gere o compose dos carros:
   ```sh
   python generate_compose.py 3
   ```
3. Edite `docker-compose.cars.yml` para usar o IP do servidor:
   ```yaml
   environment:
     - MQTT_BROKER=192.168.1.10
   ```
4. Suba os carros:
   ```sh
   docker compose -f docker-compose.cars.yml up --build
   ```

## Gerando arquivos docker-compose automaticamente

```sh
python generate_compose.py 10
```

## Como encontrar o IP do container Docker dos servidores

1. Liste os containers:
   ```sh
   docker ps
   ```
2. Descubra o IP:
   ```sh
   docker inspect -f "{{ .NetworkSettings.IPAddress }}" <CONTAINER_ID>
   ```

## Estrutura do Projeto

```
car.py                      # Simulador de carro elétrico
generate_compose.py         # Gera arquivos docker-compose
requirements.txt            # Dependências Python
constants.py                # Constantes globais
generic_server.py           # Lógica genérica dos servidores
servers/server_a.py         # Servidor A (Bahia)
servers/server_b.py         # Servidor B (Sergipe)
servers/server_c.py         # Servidor C (Alagoas)
servers/server_d.py         # Servidor D (Pernambuco)
servers/server_e.py         # Servidor E (Paraíba)
blockchain/contract.sol     # Contrato inteligente Ethereum
blockchain/deploy_contract.py # Implanta o contrato
api/transactions.py         # API para consultar transações
```

## Integração Blockchain

Registra reservas, recargas e pagamentos em um ledger Ethereum.

### Como funciona
- Usa um contrato inteligente (`contract.sol`) para gerenciar saldos e transações.
- O módulo `ledger.py` interage com o contrato via `web3.py`.
- O serviço `geth` roda no Docker Compose.

### Como rodar
- O serviço `contract_deploy` implanta o contrato automaticamente.
- Verifique os logs do `geth` para auditoria.

## Pagamentos e Contabilidade

- **Pagamentos**: Após cada recarga, o veículo paga à empresa via `/api/payment` (1% de bateria = 1e15 wei).
- **Contabilidade**: O contrato mantém saldos em wei para veículos e empresas, atualizados após cada pagamento.

## Visualização de Transações

Acesse `http://<server_ip>:5100/api/transactions` para ver o histórico de transações (reservas, recargas, pagamentos). Exemplo de resposta:
```json
[
  {
    "from": "0xAccount1",
    "to": "0xAccount2",
    "amount": 1500000000000000,
    "type": "pagamento",
    "data": "{\"vehicle_id\": \"car_1\", \"amount\": 1500000000000000, \"status\": \"COMPLETED\"}",
    "timestamp": 1623456789
  }
]
```

Consulte saldos em `http://<server_ip>:5100/api/balance/<address>`.