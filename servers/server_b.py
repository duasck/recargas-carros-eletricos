import global_utils.constants as constants
from generics.generic_server import create_server

# especific config for the server b
server_config = {
    "company": "company_b",
    "name": "b",
    "port": constants.SERVIDOR_B,
    "account": constants.COMPANY_ACCOUNTS["company_b"],
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

# create and execute the server
app, port = create_server(server_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port)