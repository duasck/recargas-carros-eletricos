PORT_BASE = 45000
SERVIDOR_A = PORT_BASE
SERVIDOR_B = PORT_BASE + 1
SERVIDOR_C = PORT_BASE + 2
SERVIDOR_D = PORT_BASE + 3
SERVIDOR_E = PORT_BASE + 4

server_a_ip = "server_a"
server_b_ip = "server_b"
server_c_ip = "server_c"
server_d_ip = "server_d"
server_e_ip = "server_e"

PORTA_MQTT = 1883
# Tópicos MQTT
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"
TOPICO_ROUTE_REQUEST = "charging/{server}/route_request"
mqtt_broker_ip = "172.16.201"

# Configurações de tempo
RESERVATION_TIMEOUT = 60  # 1 minutos em segundos
MQTT_QOS = 1  # Qualidade de serviço para MQTT
WAITING_TIMEOUT = 60  # 1 minutos para esperar resposta do servidor
TRAVEL_SPEED = 0.1  # Segundos por unidade de peso (1 km = 1 segundo)

# Consumo de bateria por km (ajustado pela taxa de descarga)
BATTERY_CONSUMPTION = {
    "fast": 1,  # 10% por 100 km
    "normal": 0.5,  # 5% por 100 km
    "slow": 0.25  # 2.5% por 100 km
}

# Servidores disponíveis
SERVERS = {
    "company_a": {
        "url": f"http://{server_a_ip}:{SERVIDOR_A}",
        "cities": ["Salvador", "Feira de Santana"]
    },
    "company_b": {
        "url": f"http://{server_b_ip}:{SERVIDOR_B}",
        "cities": ["Aracaju", "Itabaiana"]
    },
    "company_c": {
        "url": f"http://{server_c_ip}:{SERVIDOR_C}",
        "cities": ["Maceió", "Arapiraca"]
    },
    "company_d": {
        "url": f"http://{server_d_ip}:{SERVIDOR_D}",
        "cities": ["Recife", "Caruaru"]
    },
    "company_e": {
        "url": f"http://{server_e_ip}:{SERVIDOR_E}",
        "cities": ["João Pessoa", "Campina Grande"]
    }
}

servers_port = [
    {"name": "a", "port": SERVIDOR_A, "company": "company_a"},
    {"name": "b", "port": SERVIDOR_B, "company": "company_b"},
    {"name": "c", "port": SERVIDOR_C, "company": "company_c"},
    {"name": "d", "port": SERVIDOR_D, "company": "company_d"},
    {"name": "e", "port": SERVIDOR_E, "company": "company_e"}
]

# Mapeamento de cidades para estados e servidores
CITY_STATE_MAP = {
    "Salvador": {"state": "BA", "server": "server_a"},
    "Feira de Santana": {"state": "BA", "server": "server_a"},
    "Aracaju": {"state": "SE", "server": "server_b"},
    "Itabaiana": {"state": "SE", "server": "server_b"},
    "Maceió": {"state": "AL", "server": "server_c"},
    "Arapiraca": {"state": "AL", "server": "server_c"},
    "Recife": {"state": "PE", "server": "server_d"},
    "Caruaru": {"state": "PE", "server": "server_d"},
    "João Pessoa": {"state": "PB", "server": "server_e"},
    "Campina Grande": {"state": "PB", "server": "server_e"}
}

CITYS_WEIGHT = [
    ("Salvador", "Feira de Santana", {"weight": 100}),
    ("Feira de Santana", "Aracaju", {"weight": 300}),
    ("Aracaju", "Itabaiana", {"weight": 50}),
    ("Itabaiana", "Maceió", {"weight": 200}),
    ("Maceió", "Arapiraca", {"weight": 80}),
    ("Maceió", "Recife", {"weight": 250}),
    ("Recife", "Caruaru", {"weight": 120}),
    ("Recife", "João Pessoa", {"weight": 110}),
    ("João Pessoa", "Campina Grande", {"weight": 130})
]

CITYS_NODES = [
        "Salvador", "Feira de Santana", "Aracaju", "Itabaiana",
        "Maceió", "Arapiraca", "Recife", "Caruaru",
        "João Pessoa", "Campina Grande"
    ]
