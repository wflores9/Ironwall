"""
ironwall.merkle_audit.tree
───────────────────────────
Per-player input Merkle tree for match auditing.

Every player input during a match is accumulated here. The root hash is
committed to Hedera HCS at match conclusion alongside the TEE receipt.

Properties:
  • Hash function: SHA3-256 — consistent with the rest of the codebase.
    Do NOT use SHA-256 here — see WARNING in spec §08.
  • Leaf binding: HMAC-SHA3-256 with session_key — prevents leaf forgery
    without session credentials.
  • Odd-length trees: duplicate last leaf (standard practice).
  • Proof size: O(log n) sibling hashes — efficient for 1000s of inputs.
  • Storage: root committed on-chain (HCS); full leaf set optionally IPFS.

Contributing:
  #163 — Improve test coverage for InputMerkleTree edge cases
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
from typing import Literal

from ironwall.core.logging import get_logger

log = get_logger("merkle_audit.tree")

Direction = Literal["left", "right"]


def _sha3(data: str | bytes) -> str:
    """SHA3-256 hex digest. Accepts str or bytes."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha3_256(data).hexdigest()


class InputMerkleTree:
    """
    Append-only Merkle tree of player inputs.

    Each leaf is an HMAC-SHA3-256 tag over (timestamp, input_hex) under the
    authenticated session key — an attacker without the session_key cannot
    forge valid leaves.
    """

    def __init__(self) -> None:
        self.leaves: list[str] = []

    # ── Accumulation ──────────────────────────────────────────────────────

    def record_input(self, ts: int, data: bytes, session_key: bytes) -> str:
        """
        Append one input event as an authenticated leaf.

        Args:
            ts:          Input timestamp in nanoseconds.
            data:        Raw input bytes.
            session_key: 32-byte session key for HMAC binding.

        Returns the leaf hash (hex string).
        """
        msg = f"{ts}:{data.hex()}".encode()
        leaf = _hmac.new(session_key, msg, hashlib.sha3_256).hexdigest()
        self.leaves.append(leaf)
        return leaf

    # ── Root computation ──────────────────────────────────────────────────

    def root(self) -> str:
        """
        Compute and return the Merkle root hash.
        Raises ValueError if the tree is empty.
        """
        if not self.leaves:
            raise ValueError("Cannot compute root of an empty tree")

        nodes = list(self.leaves)

        while len(nodes) > 1:
            if len(nodes) % 2:
                nodes.append(nodes[-1])  # pad odd-length level
            nodes = [
                _sha3(a + b)
                for a, b in zip(nodes[::2], nodes[1::2])
            ]

        return nodes[0]

    # ── Proof generation ──────────────────────────────────────────────────

    def generate_proof(self, index: int) -> list[tuple[str, Direction]]:
        """
        Generate an inclusion proof for the leaf at *index*.

        Returns a list of (sibling_hash, direction) tuples where direction
        indicates whether the sibling is to the 'left' or 'right' of the
        current node at each level.

        Raises IndexError if *index* is out of range.
        """
        if index < 0 or index >= len(self.leaves):
            raise IndexError(f"Leaf index {index} out of range (len={len(self.leaves)})")
        return self._merkle_proof_path(index)

    def _merkle_proof_path(self, index: int) -> list[tuple[str, Direction]]:
        nodes = list(self.leaves)
        proof: list[tuple[str, Direction]] = []
        i = index

        while len(nodes) > 1:
            if len(nodes) % 2:
                nodes.append(nodes[-1])

            if i % 2 == 0:
                sibling_idx = i + 1
                direction: Direction = "right"
            else:
                sibling_idx = i - 1
                direction = "left"

            proof.append((nodes[sibling_idx], direction))

            nodes = [
                _sha3(a + b)
                for a, b in zip(nodes[::2], nodes[1::2])
            ]
            i //= 2

        return proof

    def __len__(self) -> int:
        return len(self.leaves)


# ── Standalone audit verification ─────────────────────────────────────────

def verify_proof(leaf: str, proof: list[tuple[str, Direction]], root: str) -> bool:
    """
    Verify that *leaf* is included in the Merkle tree with the given *root*.

    Args:
        leaf:  Hex leaf hash.
        proof: List of (sibling_hash, direction) from generate_proof().
        root:  Expected Merkle root hex.

    Returns True if the proof is valid, False otherwise.
    """
    node = leaf
    for sibling, direction in proof:
        if direction == "right":
            pair = node + sibling
        else:
            pair = sibling + node
        node = _sha3(pair)
    return node == root
