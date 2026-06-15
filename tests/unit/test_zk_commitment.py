"""Unit tests for canonical ZK proof commitments."""

from ironwall.zk_anticheat.commitment import (
    build_proof_commitment,
    verify_proof_commitment,
)
from ironwall.zk_anticheat.prover import ZKProver


PROOF = {"pi_a": ["1", "2"], "pi_b": [["3", "4"]], "pi_c": ["5", "6"]}
PUBLIC_SIGNALS = ["1"]
VKEY = {"protocol": "plonk", "curve": "bn128"}


def test_commitment_is_deterministic() -> None:
    first = build_proof_commitment(
        match_id="match-001",
        proof=PROOF,
        public_signals=PUBLIC_SIGNALS,
        verification_key=VKEY,
    )
    second = build_proof_commitment(
        match_id="match-001",
        proof={"pi_c": ["5", "6"], "pi_a": ["1", "2"], "pi_b": [["3", "4"]]},
        public_signals=PUBLIC_SIGNALS,
        verification_key={"curve": "bn128", "protocol": "plonk"},
    )

    assert first == second
    assert len(first.proof_hash) == 64
    assert len(first.commitment_hash()) == 64


def test_commitment_detects_tampered_proof() -> None:
    commitment = build_proof_commitment(
        match_id="match-001",
        proof=PROOF,
        public_signals=PUBLIC_SIGNALS,
        verification_key=VKEY,
    )

    assert not verify_proof_commitment(
        commitment,
        proof={"pi_a": ["tampered"]},
        public_signals=PUBLIC_SIGNALS,
        verification_key=VKEY,
    )


def test_prover_builds_commitment_from_verification_key(tmp_path) -> None:
    zkey = tmp_path / "human_constraints.zkey"
    vkey = tmp_path / "verification_key.json"
    zkey.touch()
    vkey.write_text('{"protocol":"plonk","curve":"bn128"}', encoding="utf-8")

    commitment = ZKProver(zkey_path=zkey, vkey_path=vkey).commit_proof(
        match_id="match-002",
        proof=PROOF,
        public_signals=PUBLIC_SIGNALS,
    )

    assert commitment.match_id == "match-002"
    assert commitment.circuit_id == "human_constraints_v1"
