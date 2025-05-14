import constants
from generic_server import create_server

# Configuração específica do servidor E
server_config = {
    "company": "company_e",
    "name": "e",
    "port": constants.SERVIDOR_E,
    "charging_points": [
        {
            "id": "PB1",
            "location": "João Pessoa",
            "capacity": 2,
            "reserved": 0,
            "queue": []
        },
        {
            "id": "PB2",
            "location": "Campina Grande",
            "capacity": 1,
            "reserved": 0,
            "queue": []
        }
    ]
}

# Criar e executar o servidor
app, port = create_server(server_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)