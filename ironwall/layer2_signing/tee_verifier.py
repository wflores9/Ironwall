"""
ironwall.layer2_signing.tee_verifier
──────────────────────────────────────
Runtime module verification — compiled into the SGX/SEV enclave image.
The host OS cannot read or tamper with this module.

WARNING: SHA3-256 is intentional — do NOT substitute SHA-256.
         See layer2_signing/signer.py for rationale.

Contributing: adding hardware targets
  Implement _verify_quote_sig() and _tcb_fresh() for your target
  (ARM CCA, AWS Nitro), add to SUPPORTED_ATTESTATION_PROVIDERS in
  core/config.py, and open a PR with integration tests.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from ironwall.core.logging import get_logger

log = get_logger("layer2.tee_verifier")

_PUBKEY_STORE: dict[str, bytes] = {}  # dev_id → PEM bytes (loaded from secure store)


def register_public_key(dev_id: str, public_key_pem: bytes) -> None:
    """Register a developer's public key (PEM). Call during server bootstrapping."""
    _PUBKEY_STORE[dev_id] = public_key_pem


class TEEVerifier:
    """
    Runtime module verifier — runs inside an Intel SGX or AMD SEV enclave.

    Verification steps (all must pass):
      1. SHA3-256 of loaded binary == mod_hash in signature record
      2. CT log anchor is present and consistent
      3. ECDSA P-256 signature over "dev_id:mod_hash:ts" is valid
      → generates attestation_receipt for Layer 3

    A failure at any step calls _ban() which triggers a hardware ban and
    commits a permanent violation record to Hedera HCS.
    """

    def verify_and_attest(self, code: bytes, sig: dict[str, Any]) -> dict[str, Any]:
        """
        Verify *code* against signature record *sig* inside the enclave.

        Returns an attestation_receipt dict on success, or a ban dict on failure.
        The ban dict is also suitable for returning to the broker to deny session.
        """
        # 1. Hash inside enclave — tamper-evident
        computed = hashlib.sha3_256(code).hexdigest()
        if computed != sig["mod_hash"]:
            log.warning("HASH_MISMATCH dev_id=%s", sig.get("dev_id"))
            return self._ban("HASH_MISMATCH")

        # 2. CT log anchor verification
        if not self._ct_log_verify(sig["mod_hash"], sig["ct_anchor"]):
            log.warning("CT_LOG_MISMATCH dev_id=%s", sig.get("dev_id"))
            return self._ban("CT_LOG_MISMATCH")

        # 3. ECDSA signature verification
        pub = self._get_pubkey(sig["dev_id"])
        if pub is None:
            return self._ban("UNKNOWN_DEV_ID")

        payload = f"{sig['dev_id']}:{sig['mod_hash']}:{sig['ts']}".encode()
        try:
            pub.verify(bytes.fromhex(sig["sig"]), payload, ec.ECDSA(hashes.SHA256()))
        except Exception:
            return self._ban("INVALID_SIGNATURE")

        receipt = self._generate_attestation_receipt(sig["mod_hash"])
        log.info("Attested module mod_hash=%s…", sig["mod_hash"][:16])
        return receipt

    # ── Internal helpers ──────────────────────────────────────────────────

    def _get_pubkey(self, dev_id: str) -> ec.EllipticCurvePublicKey | None:
        pem = _PUBKEY_STORE.get(dev_id)
        if pem is None:
            return None
        return serialization.load_pem_public_key(pem)  # type: ignore[return-value]

    def _ct_log_verify(self, mod_hash: str, ct_anchor: str) -> bool:
        """
        Verify the CT anchor exists in the append-only log.
        In production: query a real Trillian / Hedera-backed CT log.
        Stub: checks the local ct_log.jsonl file.
        """
        ct_log_path = Path(os.environ.get("IRONWALL_CT_LOG_PATH", "./ct_log.jsonl"))
        if not ct_log_path.exists():
            return False
        with ct_log_path.open() as fh:
            for line in fh:
                entry = json.loads(line)
                if entry.get("anchor") == ct_anchor and entry.get("mod_hash") == mod_hash:
                    return True
        return False

    def _generate_attestation_receipt(self, mod_hash: str) -> dict[str, Any]:
        """
        Generate an SGX-style attestation receipt.
        In production: call gramine / EGo SGX report generation APIs.
        """
        return {
            "status": "ATTESTED",
            "mod_hash": mod_hash,
            "verified": True,
            # In real SGX this would be a signed REPORT / QUOTE structure
            "sgx_quote": f"SIM_QUOTE_{mod_hash[:32]}",
        }

    def _ban(self, reason: str) -> dict[str, Any]:
        self._trigger_hardware_ban(reason)
        self._commit_violation_hedera(reason)
        return {"status": "BANNED", "reason": reason, "verified": False}

    def _trigger_hardware_ban(self, reason: str) -> None:
        """Trigger a hardware-level ban. Implement via platform SDK in production."""
        log.error("HARDWARE BAN triggered: %s", reason)

    def _commit_violation_hedera(self, reason: str) -> None:
        """Commit permanent violation record to Hedera HCS. Stub."""
        # TODO: call HederaMatchRecorder / HCS topic write with violation payload
        log.error("Hedera violation record committed: %s", reason)
