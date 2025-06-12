# Recargas Carros Elétricos

Este projeto simula um sistema distribuído de recarga de carros elétricos, com múltiplos servidores e clientes (carros), utilizando Flask, MQTT, Docker e blockchain Ethereum.

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação Local](#instalação-local)
- [Execução com Docker Compose](#execução-com-docker-compose)
- [Execução Manual Passo a Passo](#execução-manual-passo-a-passo)
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

## Execução Manual Passo a Passo

Para executar o sistema sem depender do `run.sh`, útil para testar partes do sistema isoladamente e entender o fluxo de execução.

### Pré-requisitos para Execução Manual
- Geth (Ethereum client)
- Docker e Docker Compose
- Python 3 com `web3`, `solcx`, `dotenv` instalados
- Arquivo `keys.json` corretamente preenchido
- Containers definidos nos arquivos `docker-compose.servers.yml` e `docker-compose.cars.yml`

### 1. Gerar os arquivos Docker Compose

Rode o script Python que cria os arquivos `docker-compose` com os serviços de servidores e carros:

```bash
python generate_compose.py 5
```

Isso criará ou atualizará os arquivos:
- `docker-compose.servers.yml`
- `docker-compose.cars.yml`

### 2. Subir apenas o Geth

Suba só o Geth para conseguir enviar ETH depois:

```bash
docker compose -f docker-compose.servers.yml up -d geth
```

### 3. Verifique se o Geth está saudável

Aguarde o healthcheck ficar OK:

```bash
docker inspect -f '{{.State.Health.Status}}' geth
```

Repita até aparecer:
```
healthy
```

### 4. Enviar ETH para o deployer

Abra o console do Geth:

```bash
docker exec -it geth geth attach http://localhost:8545
```

E, dentro do console, envie ETH para o deployer (pegue o endereço do `keys.json`):

```js
eth.sendTransaction({
  from: eth.accounts[0],
  to: "0x66B0CEEf72EB99842bE1F701198f5306b1A8f29f",
  value: web3.toWei(100, "ether")
})
```

Depois, envie ETH para os carros:

```js
eth.sendTransaction({from: eth.accounts[0], to: "0x76d8950c9a4E4C7DD8531D7f736B028CaE4b4BED", value: web3.toWei(100, "ether")})
eth.sendTransaction({from: eth.accounts[0], to: "0x862a43935a6bb4609C48aA4f7220dDac40f4cFA4", value: web3.toWei(100, "ether")})
eth.sendTransaction({from: eth.accounts[0], to: "0x3D6B78B0A8fe9e663ad55714dB087320DA63e331", value: web3.toWei(100, "ether")})
eth.sendTransaction({from: eth.accounts[0], to: "0xDD3Fa2e1415D6f3E6150381890B0F034c569962f", value: web3.toWei(100, "ether")})
eth.sendTransaction({from: eth.accounts[0], to: "0x90Bc0742d504Aef8b090Ef936DB13a146F654fcF", value: web3.toWei(100, "ether")})
```

Depois, digite `exit` para sair do console.

### 5. Fazer o deploy do contrato

Agora sim, com o deployer com saldo, rode o container que faz o deploy:

```bash
docker compose -f docker-compose.servers.yml up --build contract_deploy
```

Você deve ver uma mensagem como:
```
Contrato implantado em: 0x...
```

Isso indica que o contrato foi implantado com sucesso e o endereço está salvo no `.env`.

### 6. Subir os servidores

Agora você pode subir os demais servidores:

```bash
docker compose -f docker-compose.servers.yml up --build -d
```

### 7. Subir os carros

Por fim, suba os carros:

```bash
docker compose -f docker-compose.cars.yml up --build
```

### 8. Verificar se tudo está funcionando

Use:

```bash
docker ps
```

Verifique se os containers de:
- `geth`
- `contract_deploy` (deve ter parado com sucesso)
- `server_a`, `server_b`, ...
- `car_1`, `car_2`, ...

estão em execução ou foram iniciados corretamente.

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