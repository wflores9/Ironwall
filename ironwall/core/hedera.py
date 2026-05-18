"""
ironwall.core.hedera
────────────────────
Hedera SDK client factory. Reads HEDERA_NETWORK, HEDERA_OPERATOR_ID, and
HEDERA_OPERATOR_KEY from the environment (or .env via python-dotenv).
"""

import hashlib
import json
import os
from typing import Literal

# hedera-sdk-py — install via pip install hedera-sdk-py
try:
    from hedera import Client, AccountId, PrivateKey  # type: ignore[import]

    _SDK_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SDK_AVAILABLE = False


Network = Literal["testnet", "mainnet", "previewnet"]


def build_hedera_client(
    network: Network | None = None,
    operator_id: str | None = None,
    operator_key: str | None = None,
) -> "Client":  # type: ignore[return]
    """
    Build and return a configured Hedera SDK client.

    Parameters fall back to environment variables if not supplied:
      HEDERA_NETWORK       — testnet | mainnet | previewnet  (default: testnet)
      HEDERA_OPERATOR_ID   — 0.0.XXXXXX
      HEDERA_OPERATOR_KEY  — ED25519 private key hex / DER

    Raises RuntimeError if hedera-sdk-py is not installed.
    """
    if not _SDK_AVAILABLE:
        raise RuntimeError(
            "hedera-sdk-py is not installed. Run: pip install hedera-sdk-py"
        )

    net = (network or os.environ.get("HEDERA_NETWORK", "testnet")).lower()
    op_id = operator_id or os.environ["HEDERA_OPERATOR_ID"]
    op_key = operator_key or os.environ["HEDERA_OPERATOR_KEY"]

    match net:
        case "mainnet":
            client = Client.for_mainnet()
        case "previewnet":
            client = Client.for_previewnet()
        case _:
            client = Client.for_testnet()

    client.set_operator(AccountId.from_string(op_id), PrivateKey.from_string(op_key))
    return client


def write_ct_log_hedera(entry: dict) -> str:
    """
    Submit a CT log entry to Hedera HCS as a topic message.

    Computes sha3-256 of the sorted JSON entry as the anchor, then submits
    the full payload to the topic at HEDERA_CT_LOG_TOPIC_ID via
    TopicMessageSubmitTransaction. Degrades gracefully when the SDK is
    unavailable or the topic ID is not configured.

    Returns the anchor hash (sha3-256 of the sorted JSON entry).

    Production wiring:
        Set HEDERA_CT_LOG_TOPIC_ID, HEDERA_OPERATOR_ID, HEDERA_OPERATOR_KEY
        and uncomment the TopicMessageSubmitTransaction block below.
    """
    entry_bytes = json.dumps(entry, sort_keys=True).encode()
    anchor = hashlib.sha3_256(entry_bytes).hexdigest()

    topic_id = os.environ.get("HEDERA_CT_LOG_TOPIC_ID", "")
    if not topic_id or not _SDK_AVAILABLE:
        return anchor

    try:
        client = build_hedera_client()
        # Stub — uncomment for production:
        # from hedera import TopicMessageSubmitTransaction, TopicId
        # (
        #     TopicMessageSubmitTransaction()
        #     .set_topic_id(TopicId.from_string(topic_id))
        #     .set_message(json.dumps({"anchor": anchor, **entry}))
        #     .execute(client)
        # )
        _ = client  # suppress unused-variable warning until stub is wired
    except Exception:
        pass  # degrade gracefully — caller still receives anchor

    return anchor
