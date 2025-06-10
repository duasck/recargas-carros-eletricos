# Módulo para registrar transações no blockchain Ethereum
from web3 import Web3
import os
import json

# Conexão com o nó Ethereum
ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Endereço do contrato e ABI
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
with open('/app/blockchain/contract_abi.json', 'r') as f:
    CONTRACT_ABI = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

def get_default_account():
    try:
        accounts = w3.eth.accounts
        if accounts:
            return accounts[0]
    except Exception:
        pass
    return None

def register_identity(account, identity):
    """
    Registra uma identidade no contrato.
    """
    try:
        tx = contract.functions.registerIdentity(identity).build_transaction({
            'from': account,
            'nonce': w3.eth.get_transaction_count(account),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, os.getenv('PRIVATE_KEY'))
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        raise Exception(f'Erro ao registrar identidade: {e}')

def deposit(account, amount_wei):
    """
    Deposita saldo no contrato.
    """
    try:
        tx = contract.functions.deposit().build_transaction({
            'from': account,
            'value': amount_wei,
            'nonce': w3.eth.get_transaction_count(account),
            'gas': 200000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, os.getenv('PRIVATE_KEY'))
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        raise Exception(f'Erro ao depositar: {e}')

def registrar_transacao(tipo, dados, from_account, to_account, amount_wei=0):
    """
    Registra uma transação no contrato.
    tipo: 'reserva', 'recarga', 'pagamento'
    dados: dict com informações relevantes
    """
    try:
        data_str = json.dumps(dados)
        tx = contract.functions.recordTransaction(
            to_account, amount_wei, tipo, data_str
        ).build_transaction({
            'from': from_account,
            'nonce': w3.eth.get_transaction_count(from_account),
            'gas': 300000,
            'gasPrice': w3.eth.gas_price
        })
        signed_tx = w3.eth.account.sign_transaction(tx, os.getenv('PRIVATE_KEY'))
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()
    except Exception as e:
        raise Exception(f'Erro ao registrar transação: {e}')