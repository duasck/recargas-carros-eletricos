from web3 import Web3
import solcx
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://127.0.0.1:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

# Carrega chave do deployer a partir do keys.json
keys_path = os.path.join(root_dir, 'keys.json')
with open(keys_path, 'r') as f:
    keys_data = json.load(f)
    private_key = os.getenv('PRIVATE_KEY', keys_data["deployer"]["private_key"])

if not w3.is_connected():
    raise Exception("Não foi possível conectar ao nó Ethereum")

solcx.install_solc('0.8.0')
solcx.set_solc_version('0.8.0')

contract_path = os.path.join(script_dir, 'contract.sol')
with open(contract_path, 'r') as f:
    contract_source = f.read()

compiled = solcx.compile_source(contract_source, output_values=['abi', 'bin'])
contract_id, contract_interface = compiled.popitem()
abi = contract_interface['abi']
bytecode = contract_interface['bin']

if not private_key:
    raise ValueError("PRIVATE_KEY não definida no arquivo keys.json")

account = w3.eth.account.from_key(private_key)
contract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx = contract.constructor().build_transaction({
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 3000000,
    'gasPrice': w3.eth.gas_price
})
signed_tx = w3.eth.account.sign_transaction(tx, private_key)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

with open(os.path.join(script_dir, 'contract_abi.json'), 'w') as f:
    json.dump(abi, f, indent=4)

print(f"Contrato implantado em: {receipt.contractAddress}")

# Atualiza .env com o novo CONTRACT_ADDRESS
# with open(os.path.join(root_dir, '.env'), 'a') as f:
#     f.write(f"\nCONTRACT_ADDRESS={receipt.contractAddress}")

# Adicionar espera para garantir que o Geth está pronto
def wait_for_geth():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            if w3.is_connected():
                print(f"Geth conectado na tentativa {attempt + 1}")
                return True
        except Exception:
            pass
        print(f"Tentativa {attempt + 1}/{max_attempts}: Aguardando Geth...")
        time.sleep(2)
    return False

if __name__ == "__main__":
    print("Aguardando conexão com Geth...")
    if not wait_for_geth():
        raise Exception("Timeout ao conectar com Geth")
    
    # Salvar o endereço do contrato em um arquivo para outros serviços
    with open('/tmp/contract_address.txt', 'w') as f:
        f.write(receipt.contractAddress)
    
    print(receipt.contractAddress)  # Para captura pelo script
