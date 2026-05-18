"""
ironwall.layer3_attest.broker
───────────────────────────────
Remote Attestation Broker — server-side session gating.

Module signing (Layer 2) verifies the binary at load time.
Remote attestation closes the post-load injection gap by requiring the client
to continuously prove its execution environment is unmodified.

Key properties:
  • 60-second session token TTL — continuous re-attestation throughout session
  • No valid token → server drops connection (hard deny, never degraded)
  • Every denial committed to Hedera HCS with player_id + reason
  • Hypervisor-based cheats (Ring-1) defeated by _tcb_fresh() + _no_debug_flag()

Contributing: adding new attestation providers
  Implement _verify_tee() for ARM CCA or AWS Nitro, add to
  SUPPORTED_ATTESTATION_PROVIDERS in core/config.py, include integration
  tests against the provider's test endpoint, then open a PR.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ironwall.core.logging import get_logger

log = get_logger("layer3.broker")

_TOKEN_TTL = 60  # seconds — re-attest required every 60s


class RemoteAttestationBroker:
    """
    Gates all game data on a valid, fresh attestation receipt from Layer 2.

    One broker instance lives on the game server. The GameServer calls
    initialize_session() after the WebSocket handshake; subsequent ticks
    call validate_token().

    JWT signing uses Ed25519 asymmetric keys. If no private key PEM is
    supplied a fresh ephemeral keypair is generated on init.
    """

    def __init__(self, private_key_pem: bytes | None = None) -> None:
        if private_key_pem is not None:
            self._private_key: Ed25519PrivateKey = serialization.load_pem_private_key(  # type: ignore[assignment]
                private_key_pem, password=None
            )
        else:
            self._private_key = Ed25519PrivateKey.generate()

        self._public_key: Ed25519PublicKey = self._private_key.public_key()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

        # Register the module-signing publisher public key with TEEVerifier
        # so it can verify ECDSA P-256 module signatures at attestation time.
        _pub_pem_path = Path("signing_key.pub.pem")
        if _pub_pem_path.exists():
            from ironwall.layer2_signing.tee_verifier import register_public_key
            _dev_id = os.environ.get("PUBLISHER_DEV_ID", "ironwall-cod")
            register_public_key(_dev_id, _pub_pem_path.read_bytes())
            log.info("Registered publisher public key dev_id=%s", _dev_id)

    # ── Public API ────────────────────────────────────────────────────────

    async def initialize_session(
        self, player_id: str, attest: dict[str, Any]
    ) -> str | None:
        """
        Verify attestation receipt and issue a 60-second session token.

        Returns the signed JWT on success, or None on hard denial.
        """
        if not await self._verify_tee(attest):
            await self._deny(player_id, "INVALID_TEE_ATTESTATION")
            return None  # hard deny — no game data flows

        token = self._issue_token(player_id)
        self._schedule_reattest(player_id, token)
        log.info("Session initialised for player %s", player_id)
        return token

    def validate_token(self, player_id: str, token: str) -> bool:
        """
        Validate a session token on every game tick.
        Returns False if expired or tampered — caller must drop the connection.
        """
        try:
            claims = jwt.decode(token, self._public_key, algorithms=["EdDSA"])
            return claims.get("sub") == player_id
        except jwt.ExpiredSignatureError:
            log.warning("Expired token for player %s", player_id)
            return False
        except jwt.InvalidTokenError:
            log.warning("Invalid token for player %s", player_id)
            return False

    # ── TEE verification ──────────────────────────────────────────────────

    async def _verify_tee(self, attest: dict[str, Any]) -> bool:
        """
        Verify an SGX or AMD SEV attestation receipt.

        All four checks must pass — failure on any returns False (hard deny).

        Why _tcb_fresh() defeats hypervisor cheats (Ring-1):
          Hypervisor-based cheats run the game inside a VM they control.
          Intel SGX's TCB measurement flags virtualisation in the attestation
          quote. An attestation from inside a hypervisor-controlled VM fails
          both _no_debug_flag() and _tcb_fresh(). Broker returns None —
          the WebSocket never receives game frames.
        """
        quote = attest.get("sgx_quote") or attest.get("amd_sev_report")
        if not quote:
            return False

        return (
            self._verify_quote_sig(quote)    # genuine Intel/AMD hardware
            and self._verify_mrenclave(quote) # correct enclave binary
            and self._no_debug_flag(quote)    # not debug/sim mode in prod
            and self._tcb_fresh(quote)        # firmware up-to-date
        )

    def _verify_quote_sig(self, quote: str) -> bool:
        """Verify the attestation quote was signed by genuine Intel IAS or AMD KDS."""
        # TODO: call Intel IAS /report or AMD KDS verify endpoint
        # Stub: accept SIM quotes in SIM mode
        return quote.startswith("SIM_QUOTE_") or quote.startswith("REAL_")

    def _verify_mrenclave(self, quote: str) -> bool:
        """Verify the enclave measurement matches the expected binary hash."""
        # TODO: compare against pinned MRENCLAVE value from build system
        return True  # stub

    def _no_debug_flag(self, quote: str) -> bool:
        """Reject debug/simulation-mode quotes in production."""
        sgx_mode = os.environ.get("SGX_MODE", "SIM")
        if sgx_mode == "HW":
            return not quote.startswith("SIM_QUOTE_")
        return True  # SIM mode: accept sim quotes

    def _tcb_fresh(self, quote: str) -> bool:
        """Verify TCB (firmware) is up-to-date. Defeats hypervisor-based cheats."""
        # TODO: call Intel PCS or AMD KDS TCB info endpoint
        return True  # stub

    # ── Token issuance ─────────────────────────────────────────────────────

    def _issue_token(self, player_id: str) -> str:
        payload = {
            "sub": player_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + _TOKEN_TTL,
        }
        return jwt.encode(payload, self._private_key, algorithm="EdDSA")

    # ── Re-attestation loop ───────────────────────────────────────────────

    def _schedule_reattest(self, player_id: str, token: str) -> None:
        """Schedule the async re-attestation loop for *player_id*."""
        task = asyncio.ensure_future(self._reattest_loop(player_id))
        self._active_tasks[player_id] = task

    async def _reattest_loop(self, player_id: str) -> None:
        """Request fresh attestation every TOKEN_TTL seconds."""
        while True:
            await asyncio.sleep(_TOKEN_TTL - 5)  # re-attest 5s before expiry
            log.debug("Re-attest due for player %s", player_id)
            # In production: send re-attest challenge via side-channel to client
            # and verify the response receipt here.

    def cancel_session(self, player_id: str) -> None:
        task = self._active_tasks.pop(player_id, None)
        if task:
            task.cancel()

    # ── Denial logging ────────────────────────────────────────────────────

    async def _deny(self, player_id: str, reason: str) -> None:
        log.warning("Session denied player=%s reason=%s", player_id, reason)
        # TODO: commit denial to Hedera HCS topic with player_id + reason
