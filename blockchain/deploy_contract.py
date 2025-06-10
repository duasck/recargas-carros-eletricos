from web3 import Web3
import solcx
import json
import os

ETH_NODE_URL = os.getenv('ETH_NODE_URL', 'http://geth:8545')
w3 = Web3(Web3.HTTPProvider(ETH_NODE_URL))

solcx.install_solc('0.8.0')
solcx.set_solc_version('0.8.0')

with open('/app/blockchain/contract.sol', 'r') as f:
    contract_source = f.read()

compiled = solcx.compile_source(contract_source, output_values=['abi', 'bin'])
contract_id, contract_interface = compiled.popitem()
abi = contract_interface['abi']
bytecode = contract_interface['bin']

account = w3.eth.accounts[0]
contract = w3.eth.contract(abi=abi, bytecode=bytecode)
tx = contract.constructor().build_transaction({
    'from': account,
    'nonce': w3.eth.get_transaction_count(account),
    'gas': 2000000,
    'gasPrice': w3.eth.gas_price
})
signed_tx = w3.eth.account.sign_transaction(tx, os.getenv('PRIVATE_KEY'))
tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

with open('/app/blockchain/contract_abi.json', 'w') as f:
    json.dump(abi, f)

print(f"Contract deployed at: {receipt.contractAddress}")
os.environ['CONTRACT_ADDRESS'] = receipt.contractAddress