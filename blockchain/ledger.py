# Módulo para registrar transações no blockchain Ethereum
from web3 import Web3
import os

# Conexão com o nó Ethereum (geth)
ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Conta padrão para enviar transações (ajustar conforme necessário)
DEFAULT_ACCOUNT = w3.eth.accounts[0] if w3.eth.accounts else None

def registrar_transacao(tipo, dados):
    """
    Registra uma transação no blockchain Ethereum.
    tipo: 'reserva', 'recarga', 'pagamento'
    dados: dict com informações relevantes
    """
    if not DEFAULT_ACCOUNT:
        raise Exception('Nenhuma conta Ethereum disponível.')
    tx = {
        'from': DEFAULT_ACCOUNT,
        'to': DEFAULT_ACCOUNT,  # Transação para si mesmo, apenas para registro
        'value': 0,
        'data': w3.to_hex(text=f'{tipo}:{str(dados)}')
    }
    tx_hash = w3.eth.send_transaction(tx)
    return tx_hash.hex()
