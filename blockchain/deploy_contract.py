from web3 import Web3
import solcx
import json
import os
import time

ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Aguardar geth estar pronto
print("Conectando ao geth...")
for _ in range(30):
    if w3.is_connected():
        print("Conectado ao geth!")
        break
    print("Aguardando geth...")
    time.sleep(2)
else:
    raise ConnectionError("Falha ao conectar ao geth")

# Obter conta do keys.json ou usar uma padrão
private_key = os.getenv('PRIVATE_KEY')
if not private_key:
    raise ValueError("PRIVATE_KEY não definida no ambiente")
account = w3.eth.account.from_key(private_key)
print(f"Usando conta: {account.address}")


# --- LÓGICA DE FINANCIAMENTO DA CONTA ---

# Verificar se a conta tem fundos. Se não, transferir da conta coinbase do nó de dev.
balance = w3.eth.get_balance(account.address)
print(f"Saldo atual da conta: {w3.from_wei(balance, 'ether')} ETH")

if balance < w3.to_wei(1, 'ether'): # Se o saldo for menor que 1 ETH, financia
    print("Conta com fundos insuficientes. Tentando financiar a partir da conta coinbase do Geth...")
    try:
        # A conta coinbase é a conta pré-financiada no modo --dev
        coinbase_raw = w3.manager.request_blocking("eth_coinbase", [])
        if not coinbase_raw:
            raise ValueError("Não foi possível encontrar a conta coinbase no nó Geth.")
        
        # --- CORREÇÃO AQUI: Converter para formato Checksum ---
        coinbase = w3.to_checksum_address(coinbase_raw)
        deployer_address = w3.to_checksum_address(account.address)
        # ---------------------------------------------------

        print(f"Conta coinbase encontrada: {coinbase}")

        # Desbloquear a conta coinbase para poder enviar a transação
        print("Desbloqueando a conta coinbase...")
        w3.manager.request_blocking("personal_unlockAccount", [coinbase, "", 30])
        print("Conta coinbase desbloqueada.")

        # Quantidade de Ether para transferir (ex: 100 Ether)
        amount_to_send = w3.to_wei(100, 'ether')

        tx_hash_fund = w3.eth.send_transaction({
            'from': coinbase,
            'to': deployer_address, # Usar o endereço com checksum
            'value': amount_to_send
        })

        print(f"Enviando {w3.from_wei(amount_to_send, 'ether')} ETH para a conta {deployer_address}...")
        receipt_fund = w3.eth.wait_for_transaction_receipt(tx_hash_fund)

        new_balance = w3.eth.get_balance(deployer_address)
        print(f"Transação de financiamento concluída! Novo saldo: {w3.from_wei(new_balance, 'ether')} ETH")

    except Exception as e:
        print(f"Erro ao tentar financiar a conta: {e}")
        if "the method personal_unlockAccount does not exist" in str(e) or "personal" in str(e):
             print("\nAVISO: A API 'personal' pode não estar habilitada no Geth.")
             print("Verifique se o comando do Geth no docker-compose inclui '--http.api eth,net,web3,personal,admin'")
        raise

# --- FIM DA LÓGICA DE FINANCIAMENTO ---


solcx.install_solc('0.8.0')
solcx.set_solc_version('0.8.0')

print("Lendo contract.sol...")
try:
    with open('/app/blockchain/contract.sol', 'r') as f:
        contract_source = f.read()
except FileNotFoundError as e:
    print(f"Erro: {e}")
    raise

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
    'from': account.address,
    'nonce': w3.eth.get_transaction_count(account.address),
    'gas': 2000000,
    'gasPrice': gas_price
})

print("Assinando transação...")
signed_tx = w3.eth.account.sign_transaction(tx, private_key)
print("Enviando transação...")
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
print(f"Hash da transação: {tx_hash.hex()}")
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

# Salvar ABI e endereço
os.makedirs('/app/blockchain', exist_ok=True)
print("Salvando contract_abi.json...")
with open('/app/blockchain/contract_abi.json', 'w') as f:
    json.dump(abi, f)

print("Salvando contract_address.txt...")
with open('/app/blockchain/contract_address.txt', 'w') as f:
    f.write(receipt.contractAddress)

print(f"Contrato implantado em: {receipt.contractAddress}")
os.environ['CONTRACT_ADDRESS'] = receipt.contractAddress
