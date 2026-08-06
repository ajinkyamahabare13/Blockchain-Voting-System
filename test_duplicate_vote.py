from blockchain import contract, web3


print()
print("=" * 60)
print("BLOCKCHAIN DUPLICATE VOTE SECURITY TEST")
print("=" * 60)


# Use a Ganache account that has already voted.
# Account index 2 = user3 in your current Ganache workspace.
voter_address = web3.eth.accounts[2]

print("Testing wallet:")
print(voter_address)


# Check current election
election_id = contract.functions.electionId().call()

print()
print("Current Election ID:")
print(election_id)


# Check whether this wallet has already voted
already_voted = contract.functions.hasVoted(
    voter_address,
    election_id
).call()

print()
print("Already voted:")
print(already_voted)


if not already_voted:

    print()
    print("❌ TEST CANNOT CONTINUE")
    print("This wallet has not voted in the current election.")
    print("Choose a wallet that already voted.")
    
else:

    print()
    print("Attempting second blockchain vote...")
    print("-" * 60)

    try:

        tx_hash = contract.functions.vote(
            0
        ).transact({
            "from": voter_address
        })

        web3.eth.wait_for_transaction_receipt(
            tx_hash
        )

        print()
        print("❌ SECURITY TEST FAILED")
        print("The blockchain accepted a second vote!")
        print("Transaction:", tx_hash.hex())

    except Exception as e:

        print()
        print("✅ SECURITY TEST PASSED")
        print("Blockchain rejected the second vote.")
        print()
        print("Blockchain Error:")
        print(e)

print("=" * 60)