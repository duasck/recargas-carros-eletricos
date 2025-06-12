import json
import os

PORT_BASE = 5000
SERVIDOR_A = PORT_BASE
SERVIDOR_B = PORT_BASE + 1
SERVIDOR_C = PORT_BASE + 2
SERVIDOR_D = PORT_BASE + 3
SERVIDOR_E = PORT_BASE + 4

PORTA_MQTT = 18833
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

# --- SEÇÃO CORRIGIDA ---
# 1. Primeiro, carregamos as chaves do arquivo JSON.
try:
    with open("keys.json", "r") as f:
        KEYS = json.load(f)
except FileNotFoundError:
    print("ERRO FATAL: keys.json não encontrado. Execute generate_keys.py primeiro.")
    # Em um cenário real, você poderia ter um fallback, mas para este projeto, é melhor parar.
    exit(1)

# 2. Agora, definimos COMPANY_ACCOUNTS a partir das chaves carregadas.
COMPANY_ACCOUNTS = {c["name"]: c["address"] for c in KEYS["companies"]}

# 3. Em seguida, tentamos carregar a configuração de rede para o modo distribuído.
try:
    with open("network_config.json", "r") as f:
        NET_CONFIG = json.load(f)
    DISTRIBUTED_MODE = True
    print("INFO: network_config.json encontrado. Operando em modo distribuído.")
except FileNotFoundError:
    DISTRIBUTED_MODE = False
    print("INFO: network_config.json não encontrado. Operando em modo local (simulação).")


# 4. Finalmente, definimos os URLs dos servidores, agora que COMPANY_ACCOUNTS existe.
if DISTRIBUTED_MODE:
    SERVERS = {
        company: {"url": url, "account": COMPANY_ACCOUNTS.get(company)}
        for company, url in NET_CONFIG["servers"].items()
    }
else:
    # Modo local padrão
    SERVERS = {
        "company_a": {"url": f"http://server_a:{SERVIDOR_A}", "account": COMPANY_ACCOUNTS["company_a"]},
        "company_b": {"url": f"http://server_b:{SERVIDOR_B}", "account": COMPANY_ACCOUNTS["company_b"]},
        "company_c": {"url": f"http://server_c:{SERVIDOR_C}", "account": COMPANY_ACCOUNTS["company_c"]},
        "company_d": {"url": f"http://server_d:{SERVIDOR_D}", "account": COMPANY_ACCOUNTS["company_d"]},
        "company_e": {"url": f"http://server_e:{SERVIDOR_E}", "account": COMPANY_ACCOUNTS["company_e"]}
    }
# --- FIM DA SEÇÃO CORRIGIDA ---


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
