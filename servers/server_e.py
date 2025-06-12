import global_utils.constants as constants
from generics.generic_server import create_server

# especific config for the server e
server_config = {
    "company": "company_e",
    "name": "e",
    "port": constants.SERVIDOR_E,
    "account": constants.COMPANY_ACCOUNTS["company_e"],
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

# create and execute the server
app, port = create_server(server_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)