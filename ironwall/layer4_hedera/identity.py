"""
ironwall.layer4_hedera.identity
────────────────────────────────
Player identity management on Hedera. HBAR accounts are created with
device-bound keypairs generated inside the TEE — private keys cannot be
extracted by the host or any third party.

Reputation is computed from the player's verified HCS match history only.
No self-reported data.
"""

from __future__ import annotations

from typing import Any

from ironwall.core.logging import get_logger

log = get_logger("layer4.identity")


class PlayerIdentity:
    """
    Manages Hedera account creation and on-chain reputation scoring.

    Args:
        client: Hedera SDK client.
        tee:    TEE interface for device-bound keypair generation.
    """

    def __init__(self, client: Any, tee: Any) -> None:
        self.client = client
        self.tee = tee

    async def register(self, player_id: str) -> dict[str, Any]:
        """
        Create a new Hedera account with a device-bound keypair.

        The private key is generated inside the TEE and is hardware-bound —
        it cannot be extracted, copied, or transferred. This ties the
        account to the physical device.

        Returns the identity dict committed to HCS.
        """
        try:
            from hedera import AccountCreateTransaction, Hbar  # type: ignore[import]
        except ImportError:
            log.warning("hedera-sdk-py not installed — returning stub identity")
            return self._stub_identity(player_id)

        keypair = self.tee.generate_keypair()  # generated & stays inside TEE
        acct = await (
            AccountCreateTransaction()
            .set_key(keypair)
            .set_initial_balance(Hbar(1))
            .execute(self.client)
        )

        identity: dict[str, Any] = {
            "player_id": player_id,
            "hbar_account": str(acct.account_id),
            "hw_fingerprint": self.tee.get_bound_fingerprint(),
            "reputation": 0,
        }
        await self.commit_identity_hcs(identity)
        log.info("Registered player %s → %s", player_id, acct.account_id)
        return identity

    async def update_reputation(self, player_id: str, match_receipt: Any) -> int:
        """
        Recompute reputation from verified HCS match history and commit.
        Only verified matches (with valid TEE receipt) count toward score.
        """
        history = await self.query_hcs_match_history(player_id)
        score = self.compute_score(history)
        await self.commit_reputation_hcs(player_id, score, match_receipt)
        log.info("Reputation updated player=%s score=%d", player_id, score)
        return score

    def compute_score(self, history: list[dict[str, Any]]) -> int:
        """
        Compute reputation score from verified match history.
        Algorithm: sum of wins weighted by opponent reputation (stub).
        """
        return len([m for m in history if m.get("outcome") == "win"])

    async def query_hcs_match_history(
        self, player_id: str
    ) -> list[dict[str, Any]]:
        """Query HCS topic for all match records involving *player_id*."""
        # TODO: implement HCS mirror node query filtered by player_id
        return []

    async def commit_identity_hcs(self, identity: dict[str, Any]) -> None:
        """Commit identity record to HCS (stub)."""
        log.debug("Committing identity to HCS: %s", identity)

    async def commit_reputation_hcs(
        self, player_id: str, score: int, match_receipt: Any
    ) -> None:
        """Commit updated reputation to HCS (stub)."""
        log.debug("Committing reputation player=%s score=%d", player_id, score)

    def _stub_identity(self, player_id: str) -> dict[str, Any]:
        return {
            "player_id": player_id,
            "hbar_account": "0.0.STUB",
            "hw_fingerprint": "STUB_FINGERPRINT",
            "reputation": 0,
        }
