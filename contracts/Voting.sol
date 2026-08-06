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


    // Current election number

    uint public electionId = 1;


    // voter address => election number => voted or not

    mapping(address => mapping(uint => bool)) public hasVoted;


    // Contract owner

    address public owner;


    modifier onlyOwner() {

        require(
            msg.sender == owner,
            "Only owner can perform this action"
        );

        _;

    }


    constructor() {

        owner = msg.sender;

        addCandidate("Narendra Modi", "BJP");

        addCandidate("Rahul Gandhi", "INC");

        addCandidate("Arvind Kejriwal", "AAP");

    }


    // ==========================
    // Add Candidate
    // ==========================

    function addCandidate(
        string memory _name,
        string memory _party
    )
        public
        onlyOwner
    {

        candidates.push(

            Candidate(

                candidates.length,

                _name,

                _party,

                0

            )

        );

    }


    // ==========================
    // Vote
    // ==========================

    function vote(uint candidateId) public {

        require(
            !hasVoted[msg.sender][electionId],
            "Already voted in this election"
        );


        require(
            candidateId < candidates.length,
            "Invalid candidate"
        );


        hasVoted[msg.sender][electionId] = true;


        candidates[candidateId].voteCount++;

    }


    // ==========================
    // Reset Election
    // ==========================

    function resetElection()
        public
        onlyOwner
    {

        electionId++;


        for (
            uint i = 0;
            i < candidates.length;
            i++
        ) {

            candidates[i].voteCount = 0;

        }

    }


    // ==========================
    // Get Candidate
    // ==========================

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


    // ==========================
    // Get Candidate Count
    // ==========================

    function getCandidateCount()
        public
        view
        returns(uint)
    {

        return candidates.length;

    }

}