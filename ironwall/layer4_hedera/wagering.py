"""
ironwall.layer4_hedera.wagering
────────────────────────────────
Wagering via Hedera smart contract escrow.

Funds are locked in an EVM-compatible Solidity contract deployed on Hedera.
Neither party can withdraw unilaterally. Settlement is fully automated:
the contract reads the HCS-anchored match record (with TEE receipt) and
auto-releases funds to the winner — no manual adjudication.

Will not settle an unattested match.

Pending enhancements:
  - PLONK verifier contract on Hedera EVM
"""

from __future__ import annotations

from typing import Any

from ironwall.core.logging import get_logger

log = get_logger("layer4.wagering")


class WageringProtocol:
    """
    Wager lifecycle: create escrow → play match → settle from HCS record.

    Args:
        contract: Web3 / Hedera contract instance (wagering.sol).
        hcs_client: Interface to query HCS match records.
    """

    def __init__(self, contract: Any, hcs_client: Any) -> None:
        self.contract = contract
        self.hcs_client = hcs_client

    async def create_wager(
        self,
        player_a: str,
        player_b: str,
        amount_hbar: float,
        match_id: str,
    ) -> Any:
        """
        Lock *amount_hbar* from each player into smart-contract escrow.

        Funds cannot be withdrawn by either party until settle_wager() is
        called with a verified HCS match record.

        Args:
            player_a, player_b: HBAR account IDs (0.0.XXXXXX).
            amount_hbar: Each player's stake in HBAR.
            match_id: UUID — ties the escrow to a specific match.
        Returns the escrow transaction receipt.
        """
        condition = self._build_condition(match_id)
        amount_tinybar = int(amount_hbar * 1e8)

        log.info(
            "Creating wager match=%s players=%s/%s amount=%s HBAR",
            match_id, player_a, player_b, amount_hbar,
        )

        tx = self.contract.functions.createEscrow(
            player_a,
            player_b,
            amount_tinybar,
            condition,
        ).build_transaction({})
        return await self._submit(tx)

    async def settle_wager(
        self, match_consensus_ts: str, escrow_id: str
    ) -> Any:
        """
        Auto-settle escrow from the HCS-anchored match record.

        Fetches the HCS record at *match_consensus_ts*, verifies the TEE
        receipt, and releases funds to the winner via the smart contract.

        Raises ValueError if the match record is unattested.
        """
        record = await self._fetch_hcs_record(match_consensus_ts)

        if not record["tee_receipt"].get("verified"):
            raise ValueError("Cannot settle unattested match")

        winner = record["outcome"]["winner"]
        merkle_root = record["merkle_root"]

        log.info(
            "Settling escrow=%s winner=%s merkle_root=%s…",
            escrow_id, winner, merkle_root[:16],
        )

        tx = self.contract.functions.settleEscrow(
            escrow_id,
            winner,
            merkle_root,
        ).build_transaction({})
        return await self._submit(tx)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _build_condition(self, match_id: str) -> bytes:
        """Encode the escrow release condition (match_id → bytes)."""
        return match_id.encode()

    async def _fetch_hcs_record(self, consensus_ts: str) -> dict[str, Any]:
        """Fetch and deserialise the HCS match record at *consensus_ts*."""
        # TODO: query Hedera mirror node REST API
        return {
            "tee_receipt": {"verified": True},
            "outcome": {"winner": "0.0.STUB"},
            "merkle_root": "STUB_ROOT",
        }

    async def _submit(self, tx: Any) -> Any:
        """Submit a transaction to the Hedera EVM. Stub."""
        log.debug("Submitting transaction: %s", tx)
        return {"status": "STUB_SUBMITTED"}
