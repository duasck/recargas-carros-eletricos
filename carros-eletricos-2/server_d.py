import constants
from generic_server import create_server

# Configuração específica do servidor D
server_config = {
    "company": "company_d",
    "name": "d",
    "port": constants.SERVIDOR_D,
    "charging_points": [
        {
            "id": "PE1",
            "location": "Recife",
            "capacity": 3,
            "reserved": 0,
            "queue": []
        },
        {
            "id": "PE2",
            "location": "Caruaru",
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