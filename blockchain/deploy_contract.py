from web3 import Web3
import solcx
import json
import os
import time

ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Aguarda geth estar pronto
print("Conectando ao geth...")
for _ in range(30):
    if w3.is_connected():
        print("Conectado ao geth!")
        break
    print("Aguardando geth...")
    time.sleep(2)
else:
    raise ConnectionError("Falha ao conectar ao geth")

# Obtem a conta que vai fazer o deploy
deployer_private_key = os.getenv('PRIVATE_KEY')
if not deployer_private_key:
    raise ValueError("PRIVATE_KEY não definida no ambiente")
deployer_account = w3.eth.account.from_key(deployer_private_key)
print(f"Usando conta do deployer: {deployer_account.address}")


# LÓGICA DE FINANCIAMENTO DAS CONTAS
print("Iniciando processo de financiamento...")
try:
    with open("keys.json", "r") as f:
        KEYS = json.load(f)
    
    # Obtem a conta rica do Geth
    coinbase_raw = w3.manager.request_blocking("eth_coinbase", [])
    coinbase = w3.to_checksum_address(coinbase_raw)
    print(f"Conta coinbase (fonte dos fundos) encontrada: {coinbase}")

    # Desbloqueia a conta coinbase
    print("Desbloqueando a conta coinbase...")
    w3.manager.request_blocking("personal_unlockAccount", [coinbase, "", 300]) # Aumentar tempo de desbloqueio
    print("Conta coinbase desbloqueada.")

    # Loop para financiar todas as empresas
    for company in KEYS["companies"]:
        company_address = w3.to_checksum_address(company["address"])
        balance = w3.eth.get_balance(company_address)
        
        print(f"Verificando saldo de {company['name']} ({company_address}). Saldo atual: {w3.from_wei(balance, 'ether')} ETH")

        if balance < w3.to_wei(10, 'ether'): # Se tiver menos de 10 ETH, financia
            amount_to_send = w3.to_wei(50, 'ether') # Envia 50 ETH
            print(f"Financiando {company['name']}...")
            tx_hash = w3.eth.send_transaction({
                'from': coinbase,
                'to': company_address,
                'value': amount_to_send
            })
            w3.eth.wait_for_transaction_receipt(tx_hash)
            new_balance = w3.eth.get_balance(company_address)
            print(f"Financiamento de {company['name']} concluído! Novo saldo: {w3.from_wei(new_balance, 'ether')} ETH")
        else:
            print(f"{company['name']} já tem fundos suficientes.")

    for vehicle in KEYS["vehicles"]:
        vehicle_address = w3.to_checksum_address(vehicle["address"])
        balance = w3.eth.get_balance(vehicle_address)
        if balance < w3.to_wei(10, 'ether'):
            amount_to_send = w3.to_wei(20, 'ether')
            print(f"Financiando {vehicle['id']}...")
            tx_hash = w3.eth.send_transaction({'from': coinbase, 'to': vehicle_address, 'value': amount_to_send})
            w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Financiamento de {vehicle['id']} concluído.")

except Exception as e:
    print(f"Erro durante o processo de financiamento: {e}")
    raise

print("\nIniciando deploy do Smart Contract...")

solcx.install_solc('0.8.0')
solcx.set_solc_version('0.8.0')

print("Lendo contract.sol...")
with open('/app/blockchain/contract.sol', 'r') as f:
    contract_source = f.read()

print("Compilando contrato...")
compiled = solcx.compile_source(contract_source, output_values=['abi', 'bin'])
contract_id, contract_interface = compiled.popitem()
abi = contract_interface['abi']
bytecode = contract_interface['bin']

gas_price = w3.eth.gas_price
print(f"Usando preço do gás sugerido pelo nó: {gas_price} wei")

print("Construindo transação...")
contract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx = contract.constructor().build_transaction({
    'from': deployer_account.address,
    'nonce': w3.eth.get_transaction_count(deployer_account.address),
    'gas': 2000000,
    'gasPrice': gas_price
})

print("Assinando transação...")
signed_tx = w3.eth.account.sign_transaction(tx, deployer_private_key)
print("Enviando transação...")
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Hash da transação do deploy: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

os.makedirs('/app/blockchain', exist_ok=True)
print("Salvando contract_abi.json...")
with open('/app/blockchain/contract_abi.json', 'w') as f:
    json.dump(abi, f)

print("Salvando contract_address.txt...")
with open('/app/blockchain/contract_address.txt', 'w') as f:
    f.write(receipt.contractAddress)

print(f"Contrato implantado em: {receipt.contractAddress}")
os.environ['CONTRACT_ADDRESS'] = receipt.contractAddress
