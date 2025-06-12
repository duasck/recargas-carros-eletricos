from eth_account import Account
import json

Account.enable_unaudited_hdwallet_features()

def generate_keypair():
    account = Account.create()
    return {
        "address": account.address,
        "private_key": account._private_key.hex()
    }

def generate_keys(num_companies=5, num_vehicles=5):
    keys = {
        "companies": [],
        "vehicles": [],
        "deployer": generate_keypair()  # Chave para implantar o contrato
    }
    for i in range(num_companies):
        keypair = generate_keypair()
        keys["companies"].append({
            "name": f"company_{chr(97 + i)}",
            "address": keypair["address"],
            "private_key": keypair["private_key"]
        })
    for i in range(num_vehicles):
        keypair = generate_keypair()
        keys["vehicles"].append({
            "id": f"car_{i + 1}",
            "address": keypair["address"],
            "private_key": keypair["private_key"]
        })
    with open("keys.json", "w") as f:
        json.dump(keys, f, indent=4)
    return keys

if __name__ == "__main__":
    keys = generate_keys()
    print("Chaves geradas e salvas em keys.json:")
    print(json.dumps(keys, indent=4))