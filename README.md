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
- [Guia detalhado para rodar o projeto com Blockchain](#guia-detalhado-para-rodar-o-projeto-com-blockchain)

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
global_utils/constants.py   # Constantes globais
generics/generic_server.py  # Lógica genérica dos servidores
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

# Guia detalhado para rodar o projeto com Blockchain

Este projeto simula um sistema distribuído de recarga de carros elétricos, integrando múltiplos servidores, clientes (carros), MQTT, Docker e uma blockchain Ethereum privada com smart contract.

## 1. Pré-requisitos

- Python 3.8+ (recomendado 3.9+)
- pip
- Docker e Docker Compose
- Node.js e npm (para compilar contratos Solidity, se necessário)
- Geth (Go Ethereum) OU use o ambiente já orquestrado via Docker Compose

## 2. Instalação das dependências Python

```powershell
pip install -r requirements.txt
```

## 3. Subindo a Blockchain local

O ambiente blockchain é orquestrado via Docker Compose. Para subir os nós Ethereum e serviços relacionados:

```powershell
docker-compose -f docker-compose.servers.yml up -d
```

Se quiser simular carros também:

```powershell
docker-compose -f docker-compose.cars.yml up -d
```

## 4. Gerando chaves (opcional)

Se necessário, gere chaves para os nós/carros:

```powershell
python generate_keys.py
```

## 5. Deploy do Smart Contract

Entre na pasta `blockchain/` e execute:

```powershell
cd blockchain
python deploy_contract.py
```

Isso irá compilar e implantar o contrato, gerando `contract_abi.json` e `contract_address.txt`.

## 6. Rodando os servidores Python

Os servidores estão em `servers/`. Para rodar, por exemplo, o servidor A:

```powershell
python servers/server_a.py
```

Repita para outros servidores conforme necessário.

## 7. Rodando um carro (cliente)

```powershell
python car.py
```

Você pode configurar variáveis de ambiente para o broker MQTT, ID do veículo e chave privada, se necessário.

## 8. Consultando transações e saldos

- Transações: acesse `http://<server_ip>:5100/api/transactions`
- Saldo: acesse `http://<server_ip>:5100/api/balance/<address>`

## 9. Estrutura dos principais arquivos

- `blockchain/contract.sol`: Smart contract Solidity
- `blockchain/deploy_contract.py`: Deploy do contrato
- `blockchain/ledger.py`: Interação Python com o contrato
- `servers/server_*.py`: Servidores
- `car.py`: Simulador de carro
- `generate_keys.py`: Geração de chaves
- `docker-compose.*.yml`: Orquestração Docker

## 10. Observações

- Certifique-se de que as portas necessárias (ex: 8545) estejam liberadas.
- Os scripts Python usam Web3.py para interagir com o contrato.
- Consulte o código dos servidores para exemplos de uso das funções do contrato.
- Para dúvidas, consulte o PDF do problema ou abra uma issue.

---

Este guia detalhado complementa as instruções já existentes, focando na integração blockchain e execução ponta-a-ponta do sistema.