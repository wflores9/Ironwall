"""
ironwall.layer2_signing.signer
───────────────────────────────
Build-time module signing with ECDSA P-256.

Every executable component that runs client-side — launcher, anti-cheat agent,
input pipeline — is signed here at build time. Verification occurs at runtime
inside the SGX/SEV enclave (see tee_verifier.py).

Design decisions (from spec):
  • ECDSA P-256 over RSA-4096 — 10× smaller signatures, faster verify at scale
  • SHA3-256 (Keccak) — distinct from SHA-2; no length-extension attacks
  • Timestamp in payload — prevents valid-signature replay on a modified module
  • CT-style append-only log — stolen key usage is publicly visible
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePrivateKey,
    EllipticCurvePublicKey,
    SECP256R1,
)

from ironwall.core.hedera import write_ct_log_hedera
from ironwall.core.logging import get_logger

log = get_logger("layer2.signer")


class ModuleSigner:
    """
    Signs a module binary with ECDSA P-256 + SHA3-256 at build time.

    Args:
        private_key_pem: PEM-encoded ECDSA P-256 private key bytes.
    """

    def __init__(self, private_key_pem: bytes) -> None:
        self.key: EllipticCurvePrivateKey = serialization.load_pem_private_key(  # type: ignore[assignment]
            private_key_pem, password=None
        )
        if not isinstance(self.key.curve, SECP256R1):
            raise ValueError("Private key must use ECDSA P-256 (SECP256R1)")

    # ── Public API ────────────────────────────────────────────────────────
    def sign_module(self, code: bytes, dev_id: str) -> dict[str, Any]:
        """
        Hash and sign *code*, anchor to CT log, return the signature record.

        Returns a dict suitable for serialisation to JSON and bundled with the
        module at distribution time.
        """
        mod_hash = hashlib.sha3_256(code).hexdigest()
        ts = int(time.time())
        payload = f"{dev_id}:{mod_hash}:{ts}".encode()
        signature = self.key.sign(payload, ec.ECDSA(hashes.SHA256()))
        ct_anchor = self._anchor_ct_log(mod_hash, dev_id, ts)

        record: dict[str, Any] = {
            "dev_id": dev_id,
            "mod_hash": mod_hash,
            "sig": signature.hex(),
            "ts": ts,           # replay-attack prevention
            "ct_anchor": ct_anchor,
        }
        log.info("Signed module dev_id=%s hash=%s…", dev_id, mod_hash[:16])
        return record

    # ── Certificate Transparency append-only log ──────────────────────────
    def _anchor_ct_log(self, mod_hash: str, dev_id: str, ts: int) -> str:
        """
        Submit a CT-style entry to Hedera HCS and return the entry hash.

        Delegates to write_ct_log_hedera() which stubs the SDK call and
        degrades gracefully when HEDERA_CT_LOG_TOPIC_ID is not set.
        """
        entry = {"mod_hash": mod_hash, "dev_id": dev_id, "ts": ts}
        return write_ct_log_hedera(entry)

    # ── Key generation helper ─────────────────────────────────────────────
    @staticmethod
    def generate_key_pem() -> tuple[bytes, bytes]:
        """Generate a new ECDSA P-256 keypair. Returns (private_pem, public_pem)."""
        private_key = ec.generate_private_key(SECP256R1())
        private_pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return private_pem, public_pem
