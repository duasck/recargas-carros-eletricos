# Recargas Carros Elétricos

Este projeto simula um sistema distribuído de recarga de carros elétricos, com múltiplos servidores e clientes (carros), utilizando Flask, MQTT e Docker.

---

## Sumário

- [Pré-requisitos](#pré-requisitos)
- [Instalação Local](#instalação-local)
- [Execução com Docker Compose](#execução-com-docker-compose)
- [Execução Distribuída (2 computadores)](#execução-distribuída-2-computadores)
- [Gerando arquivos docker-compose automaticamente](#gerando-arquivos-docker-compose-automaticamente)
- [Como encontrar o IP do container Docker dos servidores](#como-encontrar-o-ip-do-container-docker-dos-servidores)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Observações](#observações)

---

## Pré-requisitos

- Python 3.9+ instalado
- [Docker](https://www.docker.com/) e [Docker Compose](https://docs.docker.com/compose/) instalados (opcional, mas recomendado)
- Broker MQTT acessível (por padrão, usa `broker.hivemq.com`)

---

## Instalação Local

1. **Clone o repositório:**
   ```sh
   git clone <url-do-repositorio>
   cd recargas-carros-eletricos
   ```

2. **Crie um ambiente virtual (opcional, mas recomendado):**
   ```sh
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Instale as dependências:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Execute um servidor (exemplo para o server_a):**
   ```sh
   python servers/server_a.py
   ```

5. **Execute um carro:**
   ```sh
   python car.py
   ```
   Você pode passar variáveis de ambiente para customizar:
   ```sh
   MQTT_BROKER=broker.hivemq.com VEHICLE_ID=car1 python car.py
   ```

---

## Execução com Docker Compose

### 1. Gerando os arquivos de compose

Você pode gerar os arquivos de compose automaticamente:

```sh
python generate_compose.py 5
```
Isso irá criar:
- `docker-compose.servers.yml` (para os servidores)
- `docker-compose.cars.yml` (para os carros, com 5 instâncias por padrão)

### 2. Subindo os servidores

```sh
docker compose -f docker-compose.servers.yml up --build
```

### 3. Subindo os carros

```sh
docker compose -f docker-compose.cars.yml up --build
```

Você pode editar o número de carros no arquivo ou gerar novamente com outro número.

---

## Execução Distribuída (2 computadores)

### Computador 1: Servidores

1. Gere e suba os servidores:
   ```sh
   python generate_compose.py
   docker compose -f docker-compose.servers.yml up --build
   ```
2. Descubra o IP deste computador (ex: `192.168.1.10`).

### Computador 2: Carros

1. Copie o projeto para este computador.
2. Gere o compose dos carros:
   ```sh
   python generate_compose.py 3
   ```
3. Edite o arquivo `docker-compose.cars.yml` e altere a variável de ambiente `MQTT_BROKER` para o IP do computador dos servidores ou para o broker MQTT desejado:
   ```yaml
   environment:
     - MQTT_BROKER=192.168.1.10
   ```
4. Suba os carros:
   ```sh
   docker compose -f docker-compose.cars.yml up --build
   ```

**Obs:** Todos os containers precisam acessar o mesmo broker MQTT.

---

## Gerando arquivos docker-compose automaticamente

O script [`generate_compose.py`](generate_compose.py) gera os arquivos de compose conforme a configuração dos servidores e o número de carros desejado.

Exemplo:
```sh
python generate_compose.py 10
```
Gera 10 carros no compose dos carros.

---

## Como encontrar o IP do container Docker dos servidores

Se você precisa que os carros (em outro computador ou rede) se conectem ao broker MQTT rodando em um container Docker dos servidores, siga os passos abaixo para descobrir o IP do container:

1. **Liste os containers em execução:**
   ```sh
   docker ps
   ```
   Anote o `CONTAINER ID` do servidor desejado.

2. **Descubra o IP do container:**
   ```sh
   docker inspect -f "{{ .NetworkSettings.IPAddress }}" <CONTAINER_ID>
   ```
   Substitua `<CONTAINER_ID>` pelo ID anotado no passo anterior.

3. **Use esse IP como valor da variável de ambiente `MQTT_BROKER` nos carros:**
   ```yaml
   environment:
     - MQTT_BROKER=<IP_ENCONTRADO>
   ```


---

## Estrutura do Projeto

```
car.py                      # Simulador de carro elétrico (cliente)
generate_compose.py         # Gera arquivos docker-compose
requirements.txt            # Dependências Python
global_utils/constants.py   # Constantes globais do sistema
generics/generic_server.py  # Lógica genérica dos servidores
servers/server_a.py         # Servidor A (Bahia)
servers/server_b.py         # Servidor B (Sergipe)
servers/server_c.py         # Servidor C (Alagoas)
servers/server_d.py         # Servidor D (Pernambuco)
servers/server_e.py         # Servidor E (Paraíba)
```

---

## Observações

- Os servidores e carros se comunicam via MQTT.
- Por padrão, utiliza o broker público `broker.hivemq.com`. Para usar outro broker, altere a variável de ambiente `MQTT_BROKER`.
- Para rodar múltiplos carros, basta aumentar o número no compose ou rodar múltiplas instâncias de `car.py`.
- Os logs dos servidores e carros mostram o fluxo de planejamento de rotas, reservas e recargas.

---

Dúvidas? Consulte os comentários nos arquivos ou abra uma issue!