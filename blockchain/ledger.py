import os
import json
import time
from web3 import Web3

ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Aguardar contract_abi.json
for _ in range(30):
    if os.path.exists('/app/blockchain/contract_abi.json'):
        with open('/app/blockchain/contract_abi.json', 'r') as f:
            CONTRACT_ABI = json.load(f)
        break
    print("Aguardando contract_abi.json...")
    time.sleep(2)
else:
    raise FileNotFoundError("contract_abi.json não encontrado após espera")

# Ler endereço do contrato
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
if not CONTRACT_ADDRESS and os.path.exists('/app/blockchain/contract_address.txt'):
    with open('/app/blockchain/contract_address.txt', 'r') as f:
        CONTRACT_ADDRESS = f.read().strip()

if not CONTRACT_ADDRESS:
    raise ValueError("CONTRACT_ADDRESS não definido")

# Converter endereço para formato checksum
checksum_address = w3.to_checksum_address(CONTRACT_ADDRESS)
contract = w3.eth.contract(address=checksum_address, abi=CONTRACT_ABI)

# --- FUNÇÕES CORRIGIDAS ---

def record_transaction(from_account, to_address, tx_type, data_dict, value=0):
    """
    Constrói uma transação para chamar a função `recordTransaction` do Smart Contract.
    
    :param from_account: O objeto da conta (com chave privada) que está enviando a transação.
    :param to_address: O endereço de destino da transação (ex: conta da empresa).
    :param tx_type: O tipo de transação (ex: 'pagamento', 'reserva').
    :param data_dict: Um dicionário Python com os dados a serem salvos. Será convertido para JSON.
    :param value: O valor em WEI a ser transferido (padrão é 0).
    :return: A transação construída, pronta para ser assinada e enviada.
    """
    from_address_checksum = w3.to_checksum_address(from_account.address)
    to_address_checksum = w3.to_checksum_address(to_address)
    
    # Converte o dicionário de dados para uma string JSON
    data_json = json.dumps(data_dict)

    tx = contract.functions.recordTransaction(
        to_address_checksum,
        value,
        tx_type,
        data_json
    ).build_transaction({
        'from': from_address_checksum,
        'value': value, # A função do contrato não é payable, mas a transação pode ter valor
        'nonce': w3.eth.get_transaction_count(from_address_checksum),
        'gas': 500000, # Um valor mais razoável para a transação
        'gasPrice': w3.eth.gas_price
    })
    return tx


def register_identity(_from, _id):
    tx = contract.functions.registerIdentity(_id).build_transaction({
        'from': w3.to_checksum_address(_from.address),
        'nonce': w3.eth.get_transaction_count(w3.to_checksum_address(_from.address)),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    return tx

def deposit(_from, _value):
    tx = contract.functions.deposit().build_transaction({
        'from': w3.to_checksum_address(_from.address),
        'value': _value,
        'nonce': w3.eth.get_transaction_count(w3.to_checksum_address(_from.address)),
        'gas': 200000,
        'gasPrice': w3.eth.gas_price
    })
    return tx
