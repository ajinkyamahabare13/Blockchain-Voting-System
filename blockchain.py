import json
from web3 import Web3

# ==========================
# Connect to Ganache
# ==========================

ganache_url = "http://127.0.0.1:7545"

web3 = Web3(Web3.HTTPProvider(ganache_url))

print("Connected:", web3.is_connected())

# ==========================
# Load Smart Contract
# ==========================

with open("build/contracts/Voting.json") as f:
    contract_json = json.load(f)

abi = contract_json["abi"]

contract_address = "0x1892D7A90F3f89D00cD7303a51033821222ADa3F"

contract = web3.eth.contract(
    address=contract_address,
    abi=abi
)

web3.eth.default_account = web3.eth.accounts[0]
print("Default Account:", web3.eth.default_account)

# ==========================
# Vote Function
# ==========================

def vote(candidate_id):

    tx_hash = contract.functions.vote(candidate_id).transact()

    web3.eth.wait_for_transaction_receipt(tx_hash)

    return tx_hash.hex()

# ==========================
# Candidate Details
# ==========================

def get_candidate(candidate_id):
    return contract.functions.getCandidate(candidate_id).call()

# ==========================
# Total Candidates
# ==========================

def get_candidate_count():
    return contract.functions.getCandidateCount().call()