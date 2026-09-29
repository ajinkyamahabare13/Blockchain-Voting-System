import json

from web3 import Web3


# ==========================
# Connect to Ganache
# ==========================

ganache_url = "http://127.0.0.1:7545"

web3 = Web3(Web3.HTTPProvider(ganache_url))



# ==========================
# Load Smart Contract
# ==========================

with open("build/contracts/Voting.json") as f:

    contract_json = json.load(f)


abi = contract_json["abi"]


contract_address = "0x71A768ab4deF9B60d52B6a314b9c71240C337654"
contract = web3.eth.contract(

    address=contract_address,

    abi=abi

)

def ensure_blockchain_connection():
    if not web3.is_connected():
        raise ConnectionError(
            "Unable to connect to Ganache."
        )
    
def get_ganache_accounts():
    if not web3.is_connected():
        raise ConnectionError(
            "Unable to connect to Ganache."
        )

    return [
        web3.to_checksum_address(account)
        for account in web3.eth.accounts
    ]


# ==========================
# Vote Function
# ==========================

def vote(candidate_id, voter_address):

    tx_hash = contract.functions.vote(
        candidate_id
    ).transact({
        "from": voter_address
    })

    web3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    return tx_hash.hex()

# ==========================
# Candidate Details
# ==========================

def get_candidate(candidate_id):

    return contract.functions.getCandidate(
        candidate_id
    ).call()

# ==========================
# Get Blockchain Vote Count
# ==========================

def get_blockchain_vote_count(candidate_id):

    candidate = contract.functions.getCandidate(
        candidate_id
    ).call()

    return candidate[3]

# ==========================
# Total Candidates
# ==========================

def get_candidate_count():

    return contract.functions.getCandidateCount().call()


# ==========================
# Reset Blockchain Election
# ==========================

def reset_election():
    owner_account = get_ganache_accounts()[0]

    tx_hash = contract.functions.resetElection().transact({
        "from": owner_account
    })

    web3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    return tx_hash.hex()

# ==========================
# Add Candidate
# ==========================

def add_candidate(name, party):

    owner_account = get_ganache_accounts()[0]

    tx_hash = contract.functions.addCandidate(
        name,
        party
    ).transact({
        "from": owner_account
    })

    web3.eth.wait_for_transaction_receipt(
        tx_hash
    )

    return tx_hash.hex()