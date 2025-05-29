# Módulo para registrar transações no blockchain Ethereum
from web3 import Web3
import os

# Conexão com o nó Ethereum (geth)
ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

def get_default_account():
    try:
        accounts = w3.eth.accounts
        if accounts:
            return accounts[0]
    except Exception:
        pass
    return None

def registrar_transacao(tipo, dados):
    """
    Registra uma transação no blockchain Ethereum.
    tipo: 'reserva', 'recarga', 'pagamento'
    dados: dict com informações relevantes
    """
    default_account = get_default_account()
    if not default_account:
        raise Exception('Nenhuma conta Ethereum disponível.')
    tx = {
        'from': default_account,
        'to': default_account,  # Transação para si mesmo, apenas para registro
        'value': 0,
        'data': w3.to_hex(text=f'{tipo}:{str(dados)}')
    }
    tx_hash = w3.eth.send_transaction(tx)
    return tx_hash.hex()
