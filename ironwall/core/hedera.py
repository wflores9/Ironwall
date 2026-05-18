"""
ironwall.core.hedera
────────────────────
Hedera SDK client factory. Reads HEDERA_NETWORK, HEDERA_OPERATOR_ID, and
HEDERA_OPERATOR_KEY from the environment (or .env via python-dotenv).
"""

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
