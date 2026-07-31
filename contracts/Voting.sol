// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Voting {

    struct Candidate {
        uint id;
        string name;
        string party;
        uint voteCount;
    }

    Candidate[] public candidates;

    mapping(address => bool) public hasVoted;

    constructor() {
        addCandidate("Narendra Modi", "BJP");
        addCandidate("Rahul Gandhi", "INC");
        addCandidate("Arvind Kejriwal", "AAP");
    }

    function addCandidate(string memory _name, string memory _party) public {
        candidates.push(
            Candidate(
                candidates.length,
                _name,
                _party,
                0
            )
        );
    }

    function vote(uint candidateId) public {

        require(!hasVoted[msg.sender], "Already voted");

        require(candidateId < candidates.length, "Invalid candidate");

        hasVoted[msg.sender] = true;

        candidates[candidateId].voteCount++;
    }

    function getCandidate(uint id)
        public
        view
        returns (
            uint,
            string memory,
            string memory,
            uint
        )
    {
        Candidate memory c = candidates[id];

        return (
            c.id,
            c.name,
            c.party,
            c.voteCount
        );
    }

    function getCandidateCount()
        public
        view
        returns(uint)
    {
        return candidates.length;
    }

}