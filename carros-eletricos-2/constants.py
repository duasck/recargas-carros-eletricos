PORT_BASE = 5000
SERVIDOR_A = PORT_BASE
SERVIDOR_B = PORT_BASE + 1
SERVIDOR_C = PORT_BASE + 2
SERVIDOR_D = PORT_BASE + 3
SERVIDOR_E = PORT_BASE + 4

# Tópicos MQTT
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"

# Configurações de tempo
RESERVATION_TIMEOUT = 300  # 5 minutos em segundos
MQTT_QOS = 1  # Qualidade de serviço para MQTT
WAITING_TIMEOUT = 600  # 10 minutos para esperar resposta do servidor
TRAVEL_SPEED = 1.0  # Segundos por unidade de peso (1 km = 1 segundo)

# Consumo de bateria por km (ajustado pela taxa de descarga)
BATTERY_CONSUMPTION = {
    "fast": 0.2,   # 0.2% por km
    "normal": 0.1, # 0.1% por km
    "slow": 0.05   # 0.05% por km
}

# Servidores disponíveis
SERVERS = {
    "company_a": {
        "url": f"http://server_a:{SERVIDOR_A}",
        "cities": ["Salvador", "Feira de Santana"]
    },
    "company_b": {
        "url": f"http://server_b:{SERVIDOR_B}",
        "cities": ["Aracaju", "Itabaiana"]
    },
    "company_c": {
        "url": f"http://server_c:{SERVIDOR_C}",
        "cities": ["Maceió", "Arapiraca"]
    },
    "company_d": {
        "url": f"http://server_d:{SERVIDOR_D}",
        "cities": ["Recife", "Caruaru"]
    },
    "company_e": {
        "url": f"http://server_e:{SERVIDOR_E}",
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