// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Interface implemented by the snarkjs-generated PLONK verifier.
interface IPlonkVerifier {
    function verifyProof(bytes calldata proof, uint256[] calldata publicSignals)
        external
        view
        returns (bool);
}

/// @notice Stores Ironwall proof commitments and optionally verifies raw PLONK proofs.
contract PlonkVerifierRegistry {
    struct ProofCommitment {
        bytes32 proofHash;
        bytes32 publicSignalsHash;
        bytes32 verifierKeyHash;
        uint64 registeredAt;
    }

    address public owner;
    IPlonkVerifier public verifier;
    bytes32 public immutable circuitId;

    mapping(bytes32 => ProofCommitment) public commitments;
    mapping(address => bool) public recorders;

    event RecorderSet(address indexed recorder, bool allowed);
    event VerifierSet(address indexed verifier);
    event ProofRegistered(
        bytes32 indexed matchId,
        bytes32 proofHash,
        bytes32 publicSignalsHash,
        bytes32 verifierKeyHash
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "IW: owner only");
        _;
    }

    modifier onlyRecorder() {
        require(recorders[msg.sender] || msg.sender == owner, "IW: recorder only");
        _;
    }

    constructor(bytes32 _circuitId, address _verifier) {
        owner = msg.sender;
        circuitId = _circuitId;
        verifier = IPlonkVerifier(_verifier);
        recorders[msg.sender] = true;
    }

    function setRecorder(address recorder, bool allowed) external onlyOwner {
        recorders[recorder] = allowed;
        emit RecorderSet(recorder, allowed);
    }

    function setVerifier(address newVerifier) external onlyOwner {
        verifier = IPlonkVerifier(newVerifier);
        emit VerifierSet(newVerifier);
    }

    function registerCommitment(
        bytes32 matchId,
        bytes32 proofHash,
        bytes32 publicSignalsHash,
        bytes32 verifierKeyHash
    ) public onlyRecorder {
        require(matchId != bytes32(0), "IW: match id required");
        commitments[matchId] = ProofCommitment({
            proofHash: proofHash,
            publicSignalsHash: publicSignalsHash,
            verifierKeyHash: verifierKeyHash,
            registeredAt: uint64(block.timestamp)
        });
        emit ProofRegistered(matchId, proofHash, publicSignalsHash, verifierKeyHash);
    }

    function verifyCommitment(
        bytes32 matchId,
        bytes32 proofHash,
        bytes32 publicSignalsHash,
        bytes32 verifierKeyHash
    ) external view returns (bool) {
        ProofCommitment memory commitment = commitments[matchId];
        return commitment.proofHash == proofHash
            && commitment.publicSignalsHash == publicSignalsHash
            && commitment.verifierKeyHash == verifierKeyHash
            && commitment.registeredAt != 0;
    }

    function verifyAndRegister(
        bytes32 matchId,
        bytes calldata proof,
        uint256[] calldata publicSignals,
        bytes32 proofHash,
        bytes32 publicSignalsHash,
        bytes32 verifierKeyHash
    ) external onlyRecorder {
        require(address(verifier) != address(0), "IW: verifier unset");
        require(verifier.verifyProof(proof, publicSignals), "IW: invalid PLONK proof");
        registerCommitment(
            matchId,
            proofHash,
            publicSignalsHash,
            verifierKeyHash
        );
    }
}
