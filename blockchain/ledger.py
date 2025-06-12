# Módulo para registrar transações no blockchain Ethereum
from web3 import Web3
import os
import json
from dotenv import load_dotenv

# Carrega variáveis do .env (como CONTRACT_ADDRESS)
load_dotenv()

# Diretórios e caminhos seguros
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)

# Conexão com o nó Ethereum
ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

if not w3.is_connected():
    raise Exception("Não foi possível conectar ao nó Ethereum")

# Verificar se o ABI existe
abi_path = os.path.join(script_dir, 'contract_abi.json')
if not os.path.exists(abi_path):
    raise FileNotFoundError(f"Contract ABI not found at {abi_path}")

# Carrega CONTRACT_ABI
with open(abi_path, 'r') as f:
    CONTRACT_ABI = json.load(f)

# Verificar se CONTRACT_ADDRESS está definido
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
if not CONTRACT_ADDRESS or CONTRACT_ADDRESS == 'None':
    raise ValueError("CONTRACT_ADDRESS not properly set in environment")

# Carrega PRIVATE_KEY do keys.json (deployer)
# keys_path = os.path.join(root_dir, 'keys.json')
# with open(keys_path, 'r') as f:
#     keys_data = json.load(f)
#     PRIVATE_KEY = keys_data["deployer"]["private_key"]
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
if not PRIVATE_KEY:
    raise ValueError("PRIVATE_KEY não definida no ambiente.")


# Instância do contrato
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
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
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
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
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
        # A assinatura agora usa a chave privada correta da empresa
        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()
    except Exception as e:
        raise Exception(f'Erro ao registrar transação: {e}')
