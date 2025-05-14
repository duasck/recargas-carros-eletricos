# Sistema de Carregamento de Veículos Elétricos

## Visão Geral
Este projeto simula um sistema de carregamento de veículos elétricos com múltiplos carros e servidores. Os carros planejam rotas e reservam pontos de carregamento usando protocolos HTTP e MQTT. O sistema suporta alta concorrência, recuperação de falhas de servidores e gerenciamento de condições críticas de bateria.

## Funcionalidades
- **Planejamento de Rotas**: Utiliza a biblioteca NetworkX para encontrar o caminho mais curto entre cidades.
- **Reservas de Carregamento**: Suporta preparação, confirmação e cancelamento de reservas via APIs HTTP.
- **Comunicação MQTT**: Mensagens em tempo real para atualizações de status de carregamento.
- **Implantação com Docker**: Executa servidores e carros em contêineres Docker com uma rede compartilhada.

## Configuração
1. **Pré-requisitos**:
   - Docker e Docker Compose
   - Python 3.9+
   - pip para instalação de dependências

2. **Instalar Dependências**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Gerar Arquivo Docker Compose**:
   ```bash
   python generate_docker_compose.py [número_de_carros]
   ```

4. **Executar o Sistema**:
   ```bash
   docker-compose up --build
   ```

## Testes
O conjunto de testes utiliza pytest para garantir confiabilidade e desempenho.

1. **Instalar Dependências de Teste**:
   ```bash
   pip install pytest pytest-mock pytest-asyncio
   ```

2. **Executar Testes**:
   ```bash
   pytest test_unit.py test_integration.py test_benchmarks.py
   ```

### Conjunto de Testes
- **Testes Unitários**: Verificam componentes individuais (por exemplo, planejamento de rotas, consumo de bateria).
- **Testes de Integração**: Simulam alta concorrência, falhas de servidores e condições críticas de bateria.
- **Benchmarks**: Medem a latência de reservas e a taxa de sucesso.

## Documentação da API
A API está documentada em `api_documentation.yaml` (formato OpenAPI). Principais endpoints:
- `GET /api/charging_points`: Lista os pontos de carregamento disponíveis.
- `POST /api/plan_route`: Planeja uma rota para um veículo.
- `POST /api/prepare`: Prepara uma reserva de carregamento.
- `POST /api/commit`: Confirma uma reserva.
- `POST /api/abort`: Cancela uma reserva.
- `GET /api/queue_status/{point_id}`: Verifica o status da fila de um ponto de carregamento.
- `GET /api/charging_status`: Obtém o status de todos os pontos de carregamento.

## Uso
1. Inicie o sistema usando Docker Compose.
2. Os carros selecionarão automaticamente cidades de início e destino e simularão a viagem.
3. Os servidores gerenciam o planejamento de rotas e reservas de carregamento.
4. Monitore os logs para acompanhar o progresso da simulação e erros.

## Benchmarks
- **Latência de Reservas**: A latência média para solicitações de reserva deve ser inferior a 0,1s.
- **Taxa de Sucesso**: Pelo menos 90% das solicitações de reserva devem ser bem-sucedidas (READY ou QUEUED).

## Contribuição
- Adicione novos testes aos arquivos `test_unit.py`, `test_integration.py` ou `test_benchmarks.py`.
- Atualize `api_documentation.yaml` para novos endpoints da API.
- Garanta que o código siga os padrões PEP 8.

## Licença
Licença MIT