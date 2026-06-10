"""
ironwall.layer4_hedera.recorder
────────────────────────────────
Commits attested match results to Hedera Consensus Service (HCS).

Why Hedera (migrated from XRPL in v5.0):
  • aBFT consensus — mathematically proven fair transaction ordering
  • Critical for wagering integrity
  • Governing Council (Google, IBM, Boeing, LG, Deutsche Telekom)

HCS creates an immutable, ordered, timestamped public record that is the
foundation for reputation scoring, wagering settlement, and third-party
data licensing.

WARNING: Will not commit an unattested match. Raises ValueError on attempt.
"""

from __future__ import annotations

import json
from typing import Any

from ironwall.core.logging import get_logger

log = get_logger("layer4.recorder")

try:
    from hedera import Client, TopicId, TopicMessageSubmitTransaction  # type: ignore[import]

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SDK_AVAILABLE = False


class HederaMatchRecorder:
    """
    Submits a verified match record to an HCS topic.

    Args:
        client:   Configured Hedera SDK Client (from core.hedera.build_hedera_client).
        topic_id: HCS topic string, e.g. "0.0.YYYYYY".
    """

    def __init__(self, client: Any, topic_id: str) -> None:
        self.client = client
        self.topic_id = TopicId.fromString(topic_id) if _SDK_AVAILABLE else topic_id

    async def commit_match_record(
        self, result: dict[str, Any], attest: dict[str, Any]
    ) -> Any:
        """
        Commit a match record to HCS.

        Args:
            result: Match result dict (id, player_ids, outcome_hash,
                    input_merkle_root, end_time).
            attest: Attestation receipt from Layer 2/3. Must have verified=True.

        Returns the HCS receipt (contains consensus_timestamp — canonical ordering).
        Raises ValueError if the match is not attested.
        """
        if not attest.get("verified"):
            raise ValueError("Unattested match — will not commit to HCS")

        record: dict[str, Any] = {
            "match_id": result["id"],
            "players": result["player_ids"],
            "outcome_hash": result["outcome_hash"],   # SHA3-256; hashed for privacy
            "merkle_root": result["input_merkle_root"],
            "tee_receipt": attest["receipt"] if "receipt" in attest else attest,
            "ts": result["end_time"],                 # Unix epoch milliseconds
        }

        msg = json.dumps(record).encode()
        log.info("Committing match %s to HCS topic %s", result["id"], self.topic_id)

        if not _SDK_AVAILABLE or self.client is None:
            log.warning("hedera-sdk-py not installed — HCS commit skipped (stub)")
            return {"consensus_timestamp": "STUB", "record": record}

        tx = (
            TopicMessageSubmitTransaction()
            .setTopicId(self.topic_id)
            .setMessage(msg)
        )
        receipt = await tx.execute(self.client)
        log.info("HCS consensus_timestamp=%s", receipt.consensus_timestamp)
        return receipt
