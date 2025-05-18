from global_utils import constants
from generics import create_server

# especific config for the server a 
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

# create and execute the server
app, port = create_server(server_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)