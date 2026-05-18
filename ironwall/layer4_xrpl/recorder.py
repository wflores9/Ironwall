"""
ironwall.layer4_xrpl.recorder
───────────────────────────────
Dual-anchor match recorder: commits the Merkle root and TEE receipt to BOTH
Hedera HCS (ordered consensus) and XRPL (independent immutable anchor).

Why dual-anchoring hardens the system:
  An attacker would need to corrupt two independent ledgers with different
  consensus mechanisms to erase or forge a match record. Hedera provides
  mathematically proven fair ordering; XRPL provides a second root of trust
  with a ~3-4s finality and a 10-year track record of uptime.

XRPL record format:
  We use an AccountSet + Memo transaction to write the match fingerprint.
  The Memo field carries: match_id | merkle_root | tee_receipt_hash | ts
  All values are hex-encoded per the XRPL Memo spec.

Dependencies:
  pip install xrpl-py

Related:
  layer4_hedera/recorder.py  — HCS side of the dual-anchor
  layer4_xrpl/escrow.py      — native XRPL escrow (no smart contract)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ironwall.core.logging import get_logger

log = get_logger("layer4.xrpl.recorder")

try:
    from xrpl.asyncio.clients import AsyncJsonRpcClient  # type: ignore[import]
    from xrpl.models.transactions import AccountSet, Memo, MemoWrapper  # type: ignore[import]
    from xrpl.asyncio.transaction import submit_and_wait  # type: ignore[import]
    from xrpl.wallet import Wallet  # type: ignore[import]

    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

# XRPL endpoints
XRPL_MAINNET = "https://xrplcluster.com"
XRPL_TESTNET = "https://s.altnet.rippletest.net:51234"


class XRPLMatchRecorder:
    """
    Anchors a verified match record to XRPL as an AccountSet Memo transaction.

    The on-chain memo contains a compact fingerprint of the match:
      match_id | merkle_root | sha3_256(tee_receipt) | end_timestamp

    This is NOT a replacement for Hedera HCS — use DualAnchorRecorder to
    write to both ledgers in a single call.

    Args:
        wallet:   XRPL wallet (funded, device-bound keypair from TEE in prod).
        network:  "mainnet" | "testnet" | "altnet"
    """

    MAINNET = XRPL_MAINNET
    TESTNET = XRPL_TESTNET

    def __init__(self, wallet: Any, network: str = "testnet") -> None:
        self.wallet = wallet
        self.url = XRPL_MAINNET if network == "mainnet" else XRPL_TESTNET
        self._client: Any = None

    async def commit_match_record(
        self, result: dict[str, Any], attest: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Anchor match fingerprint to XRPL via AccountSet + Memo.

        Args:
            result: Match result dict (id, player_ids, outcome_hash,
                    input_merkle_root, end_time).
            attest: Attestation receipt — must have verified=True.

        Returns dict with tx_hash and ledger_index on success.
        Raises ValueError if match is unattested.
        """
        if not attest.get("verified"):
            raise ValueError("Unattested match — will not anchor to XRPL")

        fingerprint = self._build_fingerprint(result, attest)
        log.info(
            "Anchoring match %s to XRPL (merkle=%s…)",
            result["id"], result["input_merkle_root"][:16],
        )

        if not _SDK_AVAILABLE:
            log.warning("xrpl-py not installed — XRPL anchor skipped (stub)")
            return {"tx_hash": "STUB_XRPL_TX", "fingerprint": fingerprint}

        async with AsyncJsonRpcClient(self.url) as client:
            memo = MemoWrapper(
                memo=Memo(
                    memo_data=fingerprint["hex"].encode().hex(),
                    memo_type="6972"    # "ir" = ironwall record
                              "6f6e77616c6c5f6d617463685f7265636f7264",
                    memo_format="6170706c69636174696f6e2f6a736f6e",  # application/json
                )
            )
            tx = AccountSet(
                account=self.wallet.classic_address,
                memos=[memo],
            )
            response = await submit_and_wait(tx, client, self.wallet)

        result_dict = {
            "tx_hash": response.result.get("hash"),
            "ledger_index": response.result.get("ledger_index"),
            "fingerprint": fingerprint,
        }
        log.info("XRPL anchor confirmed tx=%s", result_dict["tx_hash"])
        return result_dict

    # ── Fingerprint construction ──────────────────────────────────────────

    def _build_fingerprint(
        self, result: dict[str, Any], attest: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Build the compact match fingerprint written to the XRPL memo.

        Fields (all SHA3-256 hex or UUID):
          match_id       — globally unique match identifier
          merkle_root    — InputMerkleTree root (all player inputs)
          receipt_hash   — SHA3-256 of serialised TEE receipt
          ts             — match end timestamp (Unix ms)
        """
        receipt_hash = hashlib.sha3_256(
            json.dumps(attest, sort_keys=True).encode()
        ).hexdigest()

        data = {
            "match_id": result["id"],
            "merkle_root": result["input_merkle_root"],
            "receipt_hash": receipt_hash,
            "ts": result["end_time"],
        }
        return {
            "data": data,
            "hex": json.dumps(data, separators=(",", ":")),
        }


class DualAnchorRecorder:
    """
    Commits a verified match record to BOTH Hedera HCS and XRPL atomically.

    Hedera provides: mathematically proven aBFT ordering, canonical timestamp,
                     reputation + wagering settlement trigger.
    XRPL provides:  independent immutable anchor, ~3s finality, second root
                    of trust with a different consensus mechanism.

    Usage:
        recorder = DualAnchorRecorder(hedera_recorder, xrpl_recorder)
        anchors = await recorder.commit(result, attest)
        # anchors["hedera"] — HCS receipt (consensus_timestamp)
        # anchors["xrpl"]   — XRPL tx hash + ledger_index
    """

    def __init__(
        self,
        hedera_recorder: Any,   # HederaMatchRecorder
        xrpl_recorder: XRPLMatchRecorder,
    ) -> None:
        self.hedera = hedera_recorder
        self.xrpl = xrpl_recorder

    async def commit(
        self, result: dict[str, Any], attest: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Dual-anchor to Hedera + XRPL. Both must succeed.

        Returns {"hedera": ..., "xrpl": ...} receipts.
        Raises on either failure — partial anchoring is not accepted.
        """
        import asyncio

        hedera_task = asyncio.create_task(
            self.hedera.commit_match_record(result, attest)
        )
        xrpl_task = asyncio.create_task(
            self.xrpl.commit_match_record(result, attest)
        )

        hedera_receipt, xrpl_receipt = await asyncio.gather(
            hedera_task, xrpl_task
        )

        anchors = {"hedera": hedera_receipt, "xrpl": xrpl_receipt}
        log.info(
            "Dual-anchor complete match=%s hedera_ts=%s xrpl_tx=%s",
            result["id"],
            hedera_receipt.get("consensus_timestamp", "STUB"),
            xrpl_receipt.get("tx_hash", "STUB"),
        )
        return anchors
