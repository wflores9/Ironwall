"""
ironwall.core.config
────────────────────
Central configuration and feature flags loaded from the environment.
Add new attestation providers to SUPPORTED_ATTESTATION_PROVIDERS.
"""

import os
from dataclasses import dataclass, field
from typing import Literal

SGXMode = Literal["SIM", "HW"]


@dataclass(frozen=True)
class IronwallConfig:
    hedera_network: str = field(
        default_factory=lambda: os.environ.get("HEDERA_NETWORK", "testnet")
    )
    hedera_operator_id: str = field(
        default_factory=lambda: os.environ.get("HEDERA_OPERATOR_ID", "")
    )
    ironwall_topic_id: str = field(
        default_factory=lambda: os.environ.get("IRONWALL_TOPIC_ID", "")
    )
    sgx_mode: SGXMode = field(  # type: ignore[assignment]
        default_factory=lambda: os.environ.get("SGX_MODE", "SIM")
    )
    session_secret: str = field(
        default_factory=lambda: os.environ.get("SESSION_SECRET", "")
    )
    zk_trusted_setup: str = field(
        default_factory=lambda: os.environ.get("ZK_TRUSTED_SETUP", "./zk/pot18_final.ptau")
    )


# ── Attestation provider registry ──────────────────────────────────────────
# To add a new provider (e.g. ARM CCA, AWS Nitro), implement the _verify_tee()
# interface in layer3_attest/broker.py and add the provider key here.
SUPPORTED_ATTESTATION_PROVIDERS: set[str] = {
    "intel_sgx",   # Intel IAS / DCAP
    "amd_sev",     # AMD KDS
    # "arm_cca",   # TODO: #issue — contribution welcome
    # "aws_nitro",  # TODO: #issue — contribution welcome
}

CONFIG = IronwallConfig()
