"""Canonical PLONK proof commitments for on-chain verification gates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ironwall.core.crypto import sha3_256_hex


@dataclass(frozen=True)
class ProofCommitment:
    """Compact proof commitment shared by Hedera EVM and XRPL settlement gates."""

    match_id: str
    circuit_id: str
    proof_hash: str
    public_signals_hash: str
    verifier_key_hash: str

    def to_payload(self) -> dict[str, str]:
        return {
            "match_id": self.match_id,
            "circuit_id": self.circuit_id,
            "proof_hash": self.proof_hash,
            "public_signals_hash": self.public_signals_hash,
            "verifier_key_hash": self.verifier_key_hash,
        }

    def commitment_hash(self) -> str:
        return sha3_256_hex(_canonical_json(self.to_payload()))


def build_proof_commitment(
    *,
    match_id: str,
    proof: dict[str, Any],
    public_signals: list[Any],
    verification_key: dict[str, Any],
    circuit_id: str = "human_constraints_v1",
) -> ProofCommitment:
    """Build the deterministic proof commitment written to settlement layers."""
    if not match_id:
        raise ValueError("match_id is required")
    if not isinstance(proof, dict) or not proof:
        raise ValueError("proof must be a non-empty object")
    if not isinstance(public_signals, list):
        raise ValueError("public_signals must be a list")
    if not isinstance(verification_key, dict) or not verification_key:
        raise ValueError("verification_key must be a non-empty object")

    return ProofCommitment(
        match_id=match_id,
        circuit_id=circuit_id,
        proof_hash=sha3_256_hex(_canonical_json(proof)),
        public_signals_hash=sha3_256_hex(_canonical_json(public_signals)),
        verifier_key_hash=sha3_256_hex(_canonical_json(verification_key)),
    )


def verify_proof_commitment(
    commitment: ProofCommitment,
    *,
    proof: dict[str, Any],
    public_signals: list[Any],
    verification_key: dict[str, Any],
) -> bool:
    """Return True when the supplied artifacts match a commitment."""
    expected = build_proof_commitment(
        match_id=commitment.match_id,
        proof=proof,
        public_signals=public_signals,
        verification_key=verification_key,
        circuit_id=commitment.circuit_id,
    )
    return expected == commitment


def _canonical_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
