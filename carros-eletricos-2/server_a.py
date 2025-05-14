import constants
from generic_server import create_server

# Configuração específica do servidor A
server_config = {
    "company": "company_a",
    "name": "a",
    "port": constants.SERVIDOR_A,
    "charging_points": [
        {
            "id": "BA1",
            "location": "Salvador",
            "capacity": 3,
            "reserved": 0,
            "queue": []
        },
        {
            "id": "BA2",
            "location": "Feira de Santana",
            "capacity": 2,
            "reserved": 0,
            "queue": []
        }
    ]
}

# Criar e executar o servidor
app, port = create_server(server_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)