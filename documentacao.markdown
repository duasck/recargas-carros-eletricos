# Documentação do Sistema Distribuído de Recarga de Veículos Elétricos

## Introdução

Este projeto aborda o desafio de planejar e reservar pontos de recarga para veículos elétricos (VEs) durante viagens de longa distância entre cidades e estados no Brasil. O objetivo é reduzir a "ansiedade de autonomia" ao permitir reservas atômicas de pontos de recarga ao longo de uma rota, garantindo que os veículos completem suas viagens sem ficarem sem bateria. O sistema é projetado como uma arquitetura distribuída, onde múltiplos servidores (representando diferentes empresas) gerenciam pontos de recarga, e os veículos interagem com esses servidores para planejar rotas e reservar vagas de carregamento. A solução utiliza APIs REST para comunicação entre servidores e MQTT para comunicação veículo-servidor, garantindo escalabilidade e confiabilidade em um ambiente distribuído.

Este documento fornece uma visão geral da arquitetura do sistema, conceitos teóricos, metodologia, detalhes de implementação e resultados esperados, conforme exigido pelo barema do TEC502 Problema 2.

## Conceitos Principais

### Protocolo de Duas Fases (2PC)
O protocolo de Duas Fases (Two-Phase Commit) garante atomicidade nas reservas distribuídas, evitando conflitos onde múltiplos veículos reservam o mesmo ponto de recarga simultaneamente. Ele consiste em:
- **Fase de Preparação**: O servidor coordenador envia requisições `/api/prepare` para todos os servidores que gerenciam os pontos de recarga necessários. Cada servidor verifica a disponibilidade e reserva uma vaga ou coloca o veículo em uma fila.
- **Fase de Confirmação/Aborto**: Se todos os servidores retornarem `READY` ou `QUEUED`, o coordenador envia `/api/commit` para confirmar as reservas. Se algum servidor falhar (ex.: sem vagas disponíveis), o coordenador envia `/api/abort` para desfazer todas as reservas.

### MQTT (Message Queue Telemetry Transport)
O MQTT é um protocolo leve de publicação/assinatura, ideal para cenários de IoT devido ao seu baixo consumo de banda e alta confiabilidade. Os tópicos principais incluem:
- `vehicle/{server}/battery`: Para veículos reportarem o nível de bateria (não totalmente utilizado nesta implementação).
- `charging/{server}/request`: Para veículos solicitarem recarga ou sinalizarem conclusão (`action: "done"`).
- `charging/{vehicle_id}/response`: Para servidores enviarem respostas (ex.: planos de rota ou status de reserva).
- `charging/{server}/route_request`: Para veículos solicitarem planejamento de rota.

### Algoritmo de Dijkstra
O algoritmo de Dijkstra, implementado via biblioteca `networkx` (`nx.shortest_path`), calcula o caminho mais curto entre uma cidade de origem e destino com base em arestas ponderadas (distâncias) definidas em `constants.py`. Isso garante um planejamento de rota otimizado, minimizando a distância percorrida.

### Controle de Concorrência
A concorrência é gerenciada por:
- **Locks Locais**: Um `threading.Lock` (`charging_points_lock`) em `generic_server.py` previne condições de corrida ao atualizar estados dos pontos de recarga (ex.: `reserved` ou `queue`).
- **Concorrência Distribuída**: O protocolo 2PC coordena reservas entre servidores, garantindo atomicidade. Se um ponto está na capacidade máxima, os veículos são enfileirados, e o próximo veículo é notificado via MQTT quando uma vaga é liberada.

### Docker
O Docker é usado para contêinerizar servidores, veículos e o broker MQTT (Mosquitto), permitindo um ambiente distribuído realista. O script `generate_compose.py` cria arquivos `docker-compose` para automatizar a implantação de múltiplos serviços, garantindo configuração consistente e conectividade de rede.

## Arquitetura

O sistema segue uma arquitetura cliente-servidor com coordenação distribuída:
- **Servidores**: Cada servidor (`server_a.py`, `server_b.py`, etc.) representa uma empresa que gerencia pontos de recarga em cidades específicas (ex.: Salvador e Feira de Santana para `company_a`). Os servidores usam Flask para APIs REST e se conectam a um broker MQTT para comunicação com veículos.
- **Veículos**: Simulados por `car.py`, os veículos selecionam cidades de origem e destino aleatoriamente, solicitam rotas via MQTT, viajam pela rota planejada, consomem bateria e recarregam em pontos reservados.
- **Broker MQTT**: Uma instância do Mosquitto (configurada via `Dockerfile.mosquitto`) facilita a comunicação assíncrona entre veículos e servidores.
- **Rede**: Um grafo definido em `constants.py` (`CITYS_NODES`, `CITYS_WEIGHT`) modela as conexões entre cidades, usado para planejamento de rotas.

### Componentes e Seus Papéis
- **generic_server.py**: Lógica central para operações do servidor, incluindo planejamento de rotas, gerenciamento de reservas e comunicação MQTT/REST.
- **server_[a-e].py**: Arquivos de configuração para cada empresa, definindo pontos de recarga e portas.
- **car.py**: Simula o comportamento dos veículos, incluindo solicitações de rota, consumo de bateria e recarga.
- **constants.py**: Define configura	task
- **generate_compose.py**: Gera arquivos `docker-compose` para servidores e veículos.
- **Dockerfile.mosquitto**: Configura o contêiner do broker MQTT.

## Metodologia

### Abordagem de Desenvolvimento
O projeto foi desenvolvido usando uma abordagem iterativa, seguindo o cronograma de PBL:
1. **Análise de Requisitos**: Identificação dos requisitos principais (reservas distribuídas, comunicação MQTT, APIs REST, Docker).
2. **Design**: Projeto de uma arquitetura cliente-servidor com 2PC para reservas atômicas, MQTT para comunicação com veículos e Dijkstra para roteamento.
3. **Implementação**:
   - Implementação da lógica do servidor em `generic_server.py` com código reutilizável para todas as empresas.
   - Configuração de servidores individuais (`server_a.py` a `server_e.py`) com pontos de recarga específicos.
   - Desenvolvimento de `car.py` para simular o comportamento dos veículos com rotas aleatórias e consumo de bateria.
   - Uso de `generate_compose.py` para automatizar a implantação no Docker.
4. **Testes**: Testes manuais foram realizados usando ferramentas como Postman para APIs REST e MQTT Explorer para mensagens MQTT. Testes automatizados (`test_server.py`) foram propostos para validar funcionalidades principais (ver seção de Testes).
5. **Documentação**: Criação deste documento e atualização do `README.md` para atender aos requisitos do barema.

### Ferramentas e Tecnologias
- **Python**: Linguagem principal para servidores e veículos.
- **Flask**: Para implementação das APIs REST.
- **Paho-MQTT**: Para comunicação MQTT.
- **NetworkX**: Para planejamento de rotas com Dijkstra.
- **Docker**: Para contêinerização de serviços.
- **Mosquitto**: Broker MQTT.
- **PyTest**: Proposto para testes automatizados.

## Detalhes de Implementação

### Protocolos de Comunicação
- **API REST** (definida em `generic_server.py`):
  - `/api/charging_points` (GET): Lista todos os pontos de recarga de uma empresa.
  - `/api/prepare` (POST): Prepara uma reserva, retornando `READY` ou `QUEUED`.
  - `/api/commit` (POST): Confirma uma reserva preparada.
  - `/api/abort` (POST): Cancela uma reserva, liberando a vaga ou posição na fila.
  - `/api/queue_status/{point_id}` (GET): Retorna o status da fila de um ponto específico.
  - `/api/charging_status` (GET): Retorna o status de todos os pontos de recarga.
  - `/api/plan_route` (POST): Planeja uma rota com reservas de pontos de recarga.
- **MQTT** (definido em `car.py` e `generic_server.py`):
  - Veículos publicam solicitações de rota em `charging/{server}/route_request`.
  - Servidores respondem via `charging/{vehicle_id}/response`.
  - Veículos sinalizam a conclusão da recarga via `charging/{server}/request` com `action: "done"`.

### Roteamento
- **Algoritmo**: O algoritmo de Dijkstra (`nx.shortest_path`) calcula o caminho mais curto com base nas distâncias entre cidades (`CITYS_WEIGHT`).
- **Processo**: A função `plan_route_for_vehicle` em `generic_server.py` calcula o caminho mais curto e tenta reservar pontos de recarga ao longo da rota usando 2PC. Se alguma reserva falhar, todas são canceladas.

### Concorrência
- **Local**: Um `threading.Lock` garante atualizações seguras do estado dos pontos de recarga.
- **Distribuída**: O protocolo 2PC coordena reservas entre servidores, garantindo atomicidade. Se um ponto está na capacidade máxima, os veículos são enfileirados, e o próximo veículo é notificado via MQTT quando uma vaga é liberada.

### Uso de Docker
- **Servidores**: Cada servidor roda em um contêiner Docker, configurado via `docker-compose.servers.yml`.
- **Veículos**: Múltiplos veículos são simulados em contêineres, configurados via `docker-compose.cars.yml`.
- **Broker MQTT**: Roda em um contêiner usando `Dockerfile.mosquitto`.
- **Rede**: Todos os contêineres estão conectados via a rede `carros_net`.

## Testes

### Testes Manuais
- **APIs REST**: Testadas usando Postman para verificar endpoints como `/api/prepare`, `/api/commit` e `/api/plan_route`.
- **MQTT**: Testado usando MQTT Explorer para simular solicitações de veículos e verificar respostas do servidor.
- **Cenário**: Simulação de um veículo viajando de Salvador a Japão Pessoa, reservando pontos, consumindo bateria e liberando vagas.

### Testes Automatizados
Um conjunto de testes (`test_server.py`) foi proposto para validar:
- Listagem de pontos de recarga.
- Preparação, confirmação e cancelamento de reservas.
- Verificação do status da fila e dos pontos de recarga.
- Planejamento de rotas.
- Reservas concorrentes com múltiplos veículos.

Exemplo de execução de testes:
```bash
pip install pytest
pytest test_server.py -v
```

### Limitações
- **Confiabilidade**: O sistema não possui tratamento explícito para desconexões de servidores, o que pode interromper o 2PC.
- **Múltiplas Rotas**: Apenas o caminho mais curto é calculado, não todas as rotas possíveis.
- **Janelas de Tempo**: As reservas não consideram horários específicos, conforme exigido pelo problema.

## Resultados Esperados

- **Funcionalidade**: O sistema planeja rotas e reserva pontos de recarga com sucesso, garantindo atomicidade via 2PC. Veículos podem viajar, recarregar e liberar pontos, com veículos enfileirados sendo notificados quando vagas são liberadas.
- **Desempenho**: O sistema lida eficientemente com cenários de pequena escala (ex.: 5-10 veículos), com baixa latência para planejamento de rotas e reservas. O desempenho em alta carga (ex.: 100 veículos) requer testes adicionais.
- **Confiabilidade**: Embora o 2PC garanta atomicidade, mecanismos de retentativa e persistência de estado são necessários para confiabilidade em produção.
- **Usabilidade**: A API é testável via Postman, e a comunicação MQTT é adequada para cenários de IoT.

## Melhorias Futuras
- **Confiabilidade**: Adicionar lógica de retentativa para requisições HTTP/MQTT com falha e persistência de estado (ex.: SQLite) para recuperação após falhas.
- **Múltiplas Rotas**: Implementar `nx.all_shortest_paths` para oferecer rotas alternativas.
- **Janelas de Tempo**: Adicionar lógica de reserva baseada em horários.
- **Testes**: Expandir `test_server.py` para incluir testes de estresse e cenários de falha.
- **Monitoramento**: Adicionar endpoint `/api/health` e integrar Prometheus/Grafana para métricas.
- **Documentação**: Incluir link para o repositório GitHub e comentários detalhados em todas as funções.

## Conclusão
Este projeto implementa com sucesso um sistema distribuído de recarga de VEs, atendendo aos principais requisitos de planejamento de rotas, reservas atômicas e comunicação IoT. Embora atenda à maioria dos critérios do barema, melhorias em confiabilidade, testes e opções de rota alinham o sistema completamente com as expectativas do problema. O sistema é uma base robusta para uma infraestrutura escalável de recarga de VEs, com claro potencial para uso em produção com as melhorias propostas.