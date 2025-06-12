from flask import Flask, jsonify
from web3 import Web3
import json
import os
import logging

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TransactionsAPI')

# Conexão com o nó Ethereum
ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

# Endereço do contrato e ABI
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
if not CONTRACT_ADDRESS and os.path.exists('/app/blockchain/contract_address.txt'):
    with open('/app/blockchain/contract_address.txt', 'r') as f:
        CONTRACT_ADDRESS = f.read().strip()

with open('/app/blockchain/contract_abi.json', 'r') as f:
    CONTRACT_ABI = json.load(f)

contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    try:
        transactions = contract.functions.getTransactions().call()
        result = [
            {
                "from": tx[0],
                "to": tx[1],
                "amount": tx[2],
                "type": tx[3],
                "data": tx[4],
                "timestamp": tx[5]
            } for tx in transactions
        ]
        logger.info("Retrieved transaction history")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrieving transactions: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/balance/<address>', methods=['GET'])
def get_balance(address):
    try:
        balance = contract.functions.getBalance(address).call()
        logger.info(f"Retrieved balance for {address}: {balance} wei")
        return jsonify({"address": address, "balance": balance})
    except Exception as e:
        logger.error(f"Error retrieving balance: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5100)