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
    {"name": "a", "port": SERVIDOR_A},
    {"name": "b", "port": SERVIDOR_B},
    {"name": "c", "port": SERVIDOR_C},
    {"name": "d", "port": SERVIDOR_D},
    {"name": "e", "port": SERVIDOR_E}
]