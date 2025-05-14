import constants
from generic_server import create_server

# Configuração específica do servidor B
server_config = {
    "company": "company_b",
    "name": "b",
    "port": constants.SERVIDOR_B,
    "charging_points": [
        {
            "id": "SE1",
            "location": "Aracaju",
            "capacity": 2,
            "reserved": 0,
            "queue": []
        },
        {
            "id": "SE2",
            "location": "Itabaiana",
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