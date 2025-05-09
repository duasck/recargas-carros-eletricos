# Sistema Distribuído de Recarga de Veículos Elétricos

Este projeto implementa um sistema distribuído para recarga de veículos elétricos com três servidores (Empresa A: Bahia, Empresa B: Sergipe, Empresa C: Alagoas) e N carros dinâmicos gerados aleatoriamente. Os carros solicitam recarga automaticamente quando a bateria atinge 20%, usando grafos (`networkx`) para roteamento e Two-Phase Commit (2PC) para reservas atômicas. Comunicação via API REST entre servidores e MQTT para carros, tudo em contêineres Docker.

## Estrutura do Sistema

- **Empresa A (Bahia)**: Pontos em Salvador, Feira de Santana.
- **Empresa B (Sergipe)**: Pontos em Aracaju, Itabaiana.
- **Empresa C (Alagoas)**: Pontos em Maceió, Arapiraca.
- **Carros**: N veículos (`vehicle_1`, ..., `vehicle_N`) com taxas de descarga aleatórias (`fast`, `normal`, `slow`).
- **Recarga**: Carros solicitam recarga a 20% de bateria via POST a `/api/plan_route`.
- **Roteamento**: Algoritmo de Dijkstra.
- **Atomicidade**: 2PC para reservas.
- **Comunicação**: REST entre servidores, MQTT para carros.

## Pré-requisitos

- Docker e Docker Compose instalados
- Git
- Python 3.9 (para gerar `docker-compose.yml`)
- Postman ou Insomnia (para testes de API)
- Cliente MQTT (ex.: MQTT Explorer)
- Conexão com a internet (para `broker.hivemq.com`)

## Configuração

1. **Clonar o Repositório**
   ```bash
   git clone <url-do-seu-repositório>
   cd <diretório-do-repositório>
   ```

2. **Criar Arquivos do Projeto**
   Certifique-se de que os arquivos estão no diretório:
   - `server_a.py`, `server_b.py`, `server_c.py`: Servidores
   - `car.py`: Script genérico para carros
   - `generate_docker_compose.py`: Gera `docker-compose.yml`
   - `Dockerfile`: Configuração do Docker
   - `requirements.txt`: Dependências Python

3. **Gerar Docker Compose**
   Configure o número de carros (ex.: 5):
   ```bash
   python generate_docker_compose.py 5
   ```

## Executando em Uma Máquina

1. **Construir e Iniciar**
   ```bash
   docker-compose up --build
   ```
   Inicia:
   - Servidor A: `http://localhost:5000`
   - Servidor B: `http://localhost:5001`
   - Servidor C: `http://localhost:5002`
   - N carros: Publicando MQTT e solicitando recarga a 20%

2. **Monitorar**
   - Teste APIs com Postman (ex.: `GET /api/charging_points`).
   - Use MQTT Explorer no tópico `vehicle/battery` (`broker.hivemq.com:1883`).
   - Verifique logs (`docker logs <container_name>`) para acompanhar solicitações de recarga e 2PC.

## Executando em Duas Máquinas

### Máquina 1 (Servidores A e B, Metade dos Carros)
1. Copie o repositório.
2. Gere o `docker-compose.yml`:
   ```bash
   python generate_docker_compose.py <N>
   ```
3. Edite `docker-compose.yml`, removendo `server_c` e metade dos `car_*` (ex.: manter `car_1`, `car_2` para N=5).
4. Atualize `server_a.py`:
   ```python
   servers = {
       "company_b": "http://localhost:5001",
       "company_c": "http://<IP_MÁQUINA_2>:5002"
   }
   ```
   Substitua `<IP_MÁQUINA_2>` pelo IP da Máquina 2.
5. Execute:
   ```bash
   docker-compose up --build
   ```

### Máquina 2 (Servidor C, Outra Metade dos Carros)
1. Copie o repositório.
2. Crie um `docker-compose.yml` com `server_c` e os carros restantes (ex.: `car_3`, `car_4`, `car_5`):
   ```yaml
   version: '3.8'
   services:
     server_c:
       build: .
       command: python server_c.py
       ports:
         - "5002:5002"
       volumes:
         - .:/app
       environment:
         - FLASK_ENV=development
       networks:
         - charging_network
     car_3:
       build: .
       command: python car.py vehicle_3 fast
       volumes:
         - .:/app
       depends_on: [server_a]
       networks:
         - charging_network
     car_4:
       build: .
       command: python car.py vehicle_4 normal
       volumes:
         - .:/app
       depends_on: [server_a]
       networks:
         - charging_network
     car_5:
       build: .
       command: python car.py vehicle_5 slow
       volumes:
         - .:/app
       depends_on: [server_a]
       networks:
         - charging_network
   networks:
     charging_network:
       driver: bridge
   ```
3. Execute:
   ```bash
   docker-compose up --build
   ```

4. **Configurar Rede**
   - Certifique-se de que as máquinas estão na mesma rede e as portas `5000`, `5001`, `5002` estão abertas.
   - Teste a conectividade (`curl http://<IP_MÁQUINA_2>:5002/api/charging_points`).

## Testes

1. **Verificar Pontos**
   ```bash
   curl http://localhost:5000/api/charging_points  # Empresa A
   curl http://localhost:5001/api/charging_points  # Empresa B
   curl http://localhost:5002/api/charging_points  # Empresa C
   ```

2. **Monitorar Recargas**
   - Observe os logs dos carros (`docker logs car_1`) para ver solicitações de recarga a 20%.
   - Verifique logs do `server_a` para o planejamento de rotas e 2PC.

3. **Monitorar MQTT**
   - Conecte-se a `broker.hivemq.com:1883`, tópico `vehicle/battery`.

## Solução de Problemas

- **Conflitos de Porta**: Verifique `5000`, `5001`, `5002` (`sudo netstat -tuln`).
- **Erro MQTT**: Teste `ping broker.hivemq.com`.
- **Erro HTTP**: Verifique logs dos carros para erros de conexão com `server_a`.
- **Logs**: Use `docker logs <container_name>`.
