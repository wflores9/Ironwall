"""
ironwall.zk_anticheat.prover
─────────────────────────────
ZK-SNARK proof generation and verification via snarkjs (PLONK).

Players generate a proof with each input batch proving their actions were
physically achievable per the HumanConstraints circuit. The server calls
verify() on every batch — cryptographic, not heuristic.

Prerequisites:
  • `npm install` — installs snarkjs
  • `make circuits` — compiles the circom circuit + generates .zkey

Pending enhancements:
  - Benchmark proof generation time on low-end hardware
  - PLONK verifier contract on Hedera EVM
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from ironwall.core.logging import get_logger
from ironwall.zk_anticheat.commitment import ProofCommitment, build_proof_commitment

log = get_logger("zk_anticheat.prover")

_ZK_DIR = Path(os.environ.get("ZK_DIR", "./zk"))
_ZKEY = _ZK_DIR / "human_constraints.zkey"
_VKEY = _ZK_DIR / "verification_key.json"

_BATCH_SIZE = 32  # must match HumanConstraints(32) in .circom


class ZKProver:
    """
    Generates and verifies PLONK proofs for human input constraints.

    Args:
        zkey_path: Path to the .zkey file (from `make circuits`).
        vkey_path: Path to the verification_key.json.
    """

    def __init__(
        self,
        zkey_path: Path | str = _ZKEY,
        vkey_path: Path | str = _VKEY,
    ) -> None:
        self.zkey = Path(zkey_path)
        self.vkey = Path(vkey_path)

    # ── Proof generation ──────────────────────────────────────────────────

    def generate_proof(self, deltas: list[int], accel: list[int]) -> dict[str, Any]:
        """
        Generate a PLONK proof that *deltas* and *accel* satisfy HumanConstraints.

        Args:
            deltas: List of timing deltas in ms (len == BATCH_SIZE).
            accel:  List of mouse acceleration values in cm/s² (len == BATCH_SIZE).

        Returns the snarkjs proof dict.
        Raises ValueError for bad input dimensions.
        Raises subprocess.CalledProcessError if snarkjs fails.
        """
        if len(deltas) != _BATCH_SIZE or len(accel) != _BATCH_SIZE:
            raise ValueError(
                f"deltas and accel must each have exactly {_BATCH_SIZE} elements"
            )

        inputs = {
            "deltas": deltas,
            "mouse_accel": accel,
            "n_inputs": len(deltas),
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "input.json"
            proof_path = Path(tmpdir) / "proof.json"
            public_path = Path(tmpdir) / "public.json"

            input_path.write_text(json.dumps(inputs))

            subprocess.run(
                [
                    "snarkjs", "plonk", "prove",
                    str(self.zkey),
                    str(input_path),
                    str(proof_path),
                    str(public_path),
                ],
                check=True,
                capture_output=True,
            )

            proof = json.loads(proof_path.read_text())
            log.debug("Proof generated (pi_a=%s…)", str(proof.get("pi_a", ""))[:32])
            return proof

    # ── Verification ──────────────────────────────────────────────────────

    def verify(self, proof: dict[str, Any], public_signals: list[Any]) -> bool:
        """
        Verify a PLONK proof against public signals.

        Returns True if snarkjs returns OK, False otherwise.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_path = Path(tmpdir) / "proof.json"
            public_path = Path(tmpdir) / "public.json"

            proof_path.write_text(json.dumps(proof))
            public_path.write_text(json.dumps(public_signals))

            result = subprocess.run(
                [
                    "snarkjs", "plonk", "verify",
                    str(self.vkey),
                    str(public_path),
                    str(proof_path),
                ],
                capture_output=True,
            )

            ok = b"OK" in result.stdout
            log.debug("Proof verify result: %s", "OK" if ok else "FAIL")
            return ok

    def commit_proof(
        self,
        *,
        match_id: str,
        proof: dict[str, Any],
        public_signals: list[Any],
    ) -> ProofCommitment:
        """Build the proof commitment used by Hedera EVM and XRPL gates."""
        verification_key = json.loads(self.vkey.read_text(encoding="utf-8"))
        return build_proof_commitment(
            match_id=match_id,
            proof=proof,
            public_signals=public_signals,
            verification_key=verification_key,
        )

    # ── Padding helpers ───────────────────────────────────────────────────

    @staticmethod
    def pad_batch(values: list[int], fill: int = 100) -> list[int]:
        """Pad *values* to BATCH_SIZE with *fill*. Useful for partial input batches."""
        if len(values) > _BATCH_SIZE:
            raise ValueError(f"Batch too large: {len(values)} > {_BATCH_SIZE}")
        return values + [fill] * (_BATCH_SIZE - len(values))
