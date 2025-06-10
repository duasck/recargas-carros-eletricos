import global_utils.constants as constants
from generics.generic_server import create_server

# especific config for the server c
server_config = {
    "company": "company_c",
    "name": "c",
    "port": constants.SERVIDOR_C,
    "account": constants.COMPANY_ACCOUNTS["company_c"],
    "charging_points": [
        {
            "id": "AL1",
            "location": "Maceió",
            "capacity": 2,
            "reserved": 0,
            "queue": []
        },
        {
            "id": "AL2",
            "location": "Arapiraca",
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