import json
PORT_BASE = 5000
SERVIDOR_A = PORT_BASE
SERVIDOR_B = PORT_BASE + 1
SERVIDOR_C = PORT_BASE + 2
SERVIDOR_D = PORT_BASE + 3
SERVIDOR_E = PORT_BASE + 4

PORTA_MQTT = 1883
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"
TOPICO_ROUTE_REQUEST = "charging/{server}/route_request"

RESERVATION_TIMEOUT = 60
MQTT_QOS = 1
WAITING_TIMEOUT = 60
TRAVEL_SPEED = 0.1

BATTERY_CONSUMPTION = {
    "fast": 1,
    "normal": 0.5,
    "slow": 0.25
}


with open("keys.json", "r") as f:
    KEYS = json.load(f)
    COMPANY_PRIVATE_KEYS = {c["name"]: c["address"] for c in KEYS["companies"]}


   
# Contas Ethereum das empresas
COMPANY_ACCOUNTS = COMPANY_PRIVATE_KEYS = {c["name"]: c["address"] for c in KEYS["companies"]}


SERVERS = {
    "company_a": {
        "url": f"http://server_a:{SERVIDOR_A}",
        "cities": ["Salvador", "Feira de Santana"],
        "account": COMPANY_ACCOUNTS["company_a"]
    },
    "company_b": {
        "url": f"http://server_b:{SERVIDOR_B}",
        "cities": ["Aracaju", "Itabaiana"],
        "account": COMPANY_ACCOUNTS["company_b"]
    },
    "company_c": {
        "url": f"http://server_c:{SERVIDOR_C}",
        "cities": ["Maceió", "Arapiraca"],
        "account": COMPANY_ACCOUNTS["company_c"]
    },
    "company_d": {
        "url": f"http://server_d:{SERVIDOR_D}",
        "cities": ["Recife", "Caruaru"],
        "account": COMPANY_ACCOUNTS["company_d"]
    },
    "company_e": {
        "url": f"http://server_e:{SERVIDOR_E}",
        "cities": ["João Pessoa", "Campina Grande"],
        "account": COMPANY_ACCOUNTS["company_e"]
    }
}

servers_port = [
    {"name": "a", "port": SERVIDOR_A, "company": "company_a"},
    {"name": "b", "port": SERVIDOR_B, "company": "company_b"},
    {"name": "c", "port": SERVIDOR_C, "company": "company_c"},
    {"name": "d", "port": SERVIDOR_D, "company": "company_d"},
    {"name": "e", "port": SERVIDOR_E, "company": "company_e"}
]

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