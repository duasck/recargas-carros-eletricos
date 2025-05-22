## Configuração Essencial

A configuração correta do arquivo `global_utils/constants.py` é vital para o funcionamento do sistema, especialmente em um ambiente distribuído.

1.  **Endereços IP dos Servidores de Carregamento:**
    * No arquivo `global_utils/constants.py`, localize as variáveis:
        * `server_a_ip`
        * `server_b_ip`
        * `server_c_ip`
        * `server_d_ip`
        * `server_e_ip`
    * Atualize cada uma dessas variáveis com o endereço IP da máquina física (ou virtual) onde o respectivo servidor (`server_a.py`, `server_b.py`, etc.) será executado.
    * As URLs na seção `SERVERS` também devem refletir esses IPs e as portas corretas para que a comunicação HTTP entre os servidores funcione.
2.  **Endereço IP do Broker MQTT:**
    * Localize a variável `mqtt_broker_ip` em `global_utils/constants.py`.
    * Atualize esta variável com o endereço IP da máquina onde o seu broker MQTT (ex: Mosquitto) está sendo executado e acessível.
3.  **Portas:**
    * As portas base para os servidores Flask (`SERVIDOR_A` a `SERVIDOR_E`) e a porta do broker MQTT (`PORTA_MQTT`) são definidas em `constants.py`.
    * Certifique-se de que essas portas estejam disponíveis nas respectivas máquinas ou ajuste-as conforme necessário, garantindo que as mudanças sejam refletidas nas URLs em `SERVERS`.

## Executando o Projeto

Existem duas maneiras principais de executar esta simulação:

### Opção 1: Executando Tudo em uma Única Máquina (usando Docker Compose)

Esta é a abordagem recomendada para desenvolvimento e testes rápidos, pois simplifica a configuração da rede.

1.  **Instale o Docker e o Docker Compose** na sua máquina.
2.  **Inicie um Broker MQTT:**
    * Você pode executar um broker MQTT localmente usando Docker. O Mosquitto é uma escolha popular:
        ```
        docker run -d -p 18833:18833 -p 9001:9001 --name mosquitto eclipse-mosquitto
        ```
        *Nota: A porta `18833` é a usada por padrão no `constants.py`. Se você usar uma porta diferente, ajuste `PORTA_MQTT`.*
    * **Importante para Docker Compose:** No arquivo `constants.py`, para `mqtt_broker_ip`, você pode usar o IP da sua máquina host (se o Mosquitto estiver rodando diretamente no host) ou, se o Mosquitto também for um serviço Docker na mesma rede, você pode usar o nome do serviço Docker (ex: `mosquitto`). Para simplificar ao rodar carros e servidores como contêineres, o ideal é adicionar o Mosquitto ao `docker-compose.servers.yml` ou `docker-compose.cars.yml` e usar seu nome de serviço. Alternativamente, para contêineres acessarem um serviço no host, `host.docker.internal` pode ser usado como `mqtt_broker_ip` (verifique a documentação do Docker para seu SO). Para este guia, assumiremos que o Mosquitto está acessível pelo IP configurado.
3.  **Gere os Arquivos Docker Compose:**
    * O script `generate_compose.py` cria os arquivos `docker-compose.servers.yml` (para os servidores de carregamento) e `docker-compose.cars.yml` (para os veículos).
    * Você pode especificar o número de carros a serem simulados como um argumento de linha de comando. O padrão é 5.
        ```
        python generate_compose.py <numero_de_carros>
        # Exemplo para simular 10 carros:
        # python generate_compose.py 10
        ```
    * **Ajuste para Docker (Opcional, mas recomendado):** Se você estiver rodando o MQTT broker como um container chamado `mosquitto` na mesma rede Docker (`carros_net`), você pode modificar `generate_compose.py` para que ele configure `MQTT_BROKER=mosquitto` como variável de ambiente para os contêineres dos carros. E em `constants.py`, `mqtt_broker_ip` pode ser configurado para `mosquitto` quando os servidores também rodam em Docker.
4.  **Construa e Execute os Contêineres:**
    * Abra dois terminais separados no diretório raiz do projeto.
    * **Terminal 1 (Servidores):**
        ```
        docker-compose -f docker-compose.servers.yml up --build
        ```
    * **Terminal 2 (Carros):**
        ```
        docker-compose -f docker-compose.cars.yml up --build
        ```
    * Os servidores serão iniciados e, em seguida, os carros começarão suas simulações. Você poderá acompanhar os logs de cada contêiner nos respectivos terminais.

### Opção 2: Executando Servidores em Múltiplas Máquinas (Ambiente Distribuído)

Esta abordagem permite distribuir os servidores de carregamento em diferentes máquinas na sua rede. Os carros podem rodar em qualquer uma dessas máquinas ou em máquinas dedicadas.

1.  **Instale as Dependências:**
    * Em **cada máquina** que executará um ou mais componentes do sistema (servidores ou carros), certifique-se de que Python e as bibliotecas listadas em `requirements.txt` estão instalados.
2.  **Configure e Inicie o Broker MQTT:**
    * Escolha **uma máquina** na sua rede para hospedar o broker MQTT (ex: Mosquitto). Instale e inicie o Mosquitto nesta máquina.
    * Anote o endereço IP desta máquina. Este será o seu `mqtt_broker_ip`.
3.  **Distribua e Configure o Código do Projeto:**
    * Copie o código do projeto para todas as máquinas que participarão da simulação.
    * Em **cada cópia** do projeto, edite o arquivo `global_utils/constants.py`:
        * Configure `mqtt_broker_ip` com o IP da máquina onde o Mosquitto está rodando.
        * Configure `server_a_ip`, `server_b_ip`, etc., com os IPs corretos das máquinas onde cada servidor específico (`server_a.py`, `server_b.py`, etc.) será executado.
        * Verifique se as URLs em `SERVERS` estão corretas, usando os IPs e portas configurados.
4.  **Execute os Servidores de Carregamento:**
    * Em cada máquina designada para um servidor, navegue até o diretório raiz do projeto e execute o script do servidor correspondente.
    * **Máquina para Server A (ex: IP 192.168.1.101):**
        ```
        python servers/server_a.py
        ```
    * **Máquina para Server B (ex: IP 192.168.1.102):**
        ```
        python servers/server_b.py
        ```
    * ... e assim por diante para `server_c.py`, `server_d.py`, e `server_e.py` em suas respectivas máquinas. Certifique-se de que os firewalls permitam a comunicação nas portas especificadas.
5.  **Execute os Carros:**
    * Os carros podem ser executados em qualquer máquina que tenha acesso de rede ao broker MQTT e aos servidores HTTP (Flask). Pode ser uma das máquinas dos servidores ou máquinas separadas.
    * Certifique-se de que o `constants.py` na máquina onde o carro será executado também esteja corretamente configurado com todos os IPs.
    * Você pode executar múltiplos scripts `car.py`, cada um em seu próprio terminal ou como processos em segundo plano.
        ```
        # Exemplo para o primeiro carro na máquina X
        python car.py veiculo_001 normal

        # Exemplo para o segundo carro na máquina Y (ou mesma máquina, outro terminal)
        python car.py veiculo_002 fast
        ```
    * O script `car.py` aceita o ID do veículo e a taxa de descarga (`fast`, `normal`, `slow`) como argumentos de linha de comando. Se não fornecidos, eles podem ser definidos via variáveis de ambiente (`VEHICLE_ID`, `DISCHARGE_RATE`) ou usarão valores aleatórios/padrão.

## Fluxo de Funcionamento (Resumido)

1.  **Inicialização:**
    * Os servidores (`server_a` a `server_e`) iniciam, configuram seus pontos de carregamento e se conectam ao broker MQTT.
    * Cada servidor se inscreve em tópicos MQTT relevantes para receber solicitações de planejamento de rota e de gerenciamento de carregamento (reservas, finalizações).
2.  **Planejamento de Rota pelo Veículo:**
    * Uma instância de `car.py` (veículo) determina uma cidade de partida e uma cidade de destino.
    * O veículo publica uma mensagem MQTT no tópico `charging/{server}/route_request` (onde `{server}` é o servidor associado à sua cidade de partida) solicitando um plano de rota.
3.  **Processamento da Rota pelo Servidor:**
    * O servidor que recebe a solicitação calcula a rota mais curta usando `networkx`.
    * Em seguida, ele tenta reservar os pontos de carregamento necessários ao longo desta rota. Este processo utiliza um protocolo de confirmação de duas fases (2PC) para garantir a atomicidade das reservas distribuídas:
        * **Fase de Preparação:** O servidor coordenador envia requisições HTTP POST para o endpoint `/api/prepare` dos outros servidores, se pontos gerenciados por eles forem necessários.
        * **Fase de Confirmação/Aborto:** Se todos os servidores envolvidos confirmarem a preparação (`READY` ou `QUEUED`), o coordenador envia requisições `/api/commit`. Se alguma preparação falhar, ele envia requisições `/api/abort` para todos que prepararam.
    * O resultado final (plano de rota com reservas confirmadas, ou uma mensagem de erro) é enviado de volta ao veículo via MQTT, no tópico `charging/{vehicle_id}/response`.
4.  **Simulação da Viagem e Carregamento:**
    * O veículo simula o deslocamento entre as cidades da rota, consumindo bateria.
    * Ao chegar em uma cidade onde possui uma reserva, ele simula o processo de recarga.
    * Quando o carregamento é concluído, o veículo publica uma mensagem MQTT com `action: "done"` para o tópico `charging/{server}/request` do servidor que gerencia aquele ponto.
    * O servidor então libera o ponto de carregamento e, se houver outros veículos na fila para aquele ponto, notifica o próximo da fila.

## Tópicos MQTT Chave

* `vehicle/{server}/battery`: (Teoricamente para veículos publicarem seu nível de bateria; atualmente, os servidores apenas registram essa informação se recebida).
* `charging/{server}/request`: Usado por veículos para solicitar uma reserva em um ponto específico de um servidor (embora a reserva principal seja via 2PC no planejamento de rota) ou, mais importante, para indicar que o carregamento foi concluído (`action: "done"`).
* `charging/{vehicle_id}/response`: Tópico dedicado para cada veículo, onde os servidores enviam respostas diretas (confirmações de reserva de rota, status de "pronto para carregar" quando sai da fila, erros).
* `charging/{server}/route_request`: Usado por veículos para enviar solicitações de planejamento de rota para um servidor específico (geralmente o servidor da cidade de partida).