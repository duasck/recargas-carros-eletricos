PORT_BASE = 5000
SERVIDOR_A = PORT_BASE
SERVIDOR_B = PORT_BASE + 1
SERVIDOR_C = PORT_BASE + 2

# Tópicos MQTT
TOPICO_BATERIA = "vehicle/{server}/battery"
TOPICO_RESERVA = "charging/{server}/request"
TOPICO_RESPOSTA = "charging/{vehicle_id}/response"