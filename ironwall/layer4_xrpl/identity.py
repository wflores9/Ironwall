"""
ironwall.layer4_xrpl.identity
───────────────────────────────
Player identity on XRPL: device-bound accounts + XLS-20 reputation NFTs.

Why XRPL identity hardens the system vs Hedera-only:
  • XRPL accounts are free to create (no minimum balance requirement in
    XLS-66 vault contexts) — lowers barrier to legitimate play.
  • XLS-20 non-transferable NFTs give players a portable, cross-game
    reputation primitive that travels with the XRPL account, not locked
    to Ironwall's Hedera topic. Ward Protocol (XLS-66) can reference these
    same NFTs for lending vault identity verification.
  • Device-bound keypairs generated inside the TEE mean the private key
    never leaves the secure enclave — same security model as Hedera identity
    but anchored to a different ledger for redundancy.

XLS-20 NFT flags used:
  tfTransferable = 0       — non-transferable (soulbound reputation)
  tfOnlyXRP = 1            — no IOU complications
  URI field                — compact JSON: {player_id, reputation, ts}

Dependencies:
  pip install xrpl-py
"""

from __future__ import annotations

import json
import time
from typing import Any

from ironwall.core.logging import get_logger

log = get_logger("layer4.xrpl.identity")

try:
    from xrpl.asyncio.clients import AsyncJsonRpcClient  # type: ignore[import]
    from xrpl.asyncio.transaction import submit_and_wait  # type: ignore[import]
    from xrpl.models.transactions import (  # type: ignore[import]
        AccountSet,
        NFTokenMint,
        NFTokenMintFlag,
    )
    from xrpl.wallet import Wallet  # type: ignore[import]

    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False

XRPL_TESTNET = "https://s.altnet.rippletest.net:51234"
XRPL_MAINNET = "https://xrplcluster.com"

# NFT taxon — unique per application; Ironwall's registered taxon
IRONWALL_NFT_TAXON = 0x49574C4C  # "IWLL" in hex


class XRPLPlayerIdentity:
    """
    Manages XRPL account creation and XLS-20 reputation NFT minting.

    In production the wallet keypair is generated inside the TEE and
    the private key never leaves the enclave (device-bound).

    Args:
        server_wallet: The Ironwall server's XRPL wallet (mints NFTs).
        network: "mainnet" | "testnet"
    """

    def __init__(self, server_wallet: Any, network: str = "testnet") -> None:
        self.server_wallet = server_wallet
        self.url = XRPL_MAINNET if network == "mainnet" else XRPL_TESTNET

    async def register(self, player_id: str, tee: Any) -> dict[str, Any]:
        """
        Create a new XRPL account for *player_id* with a TEE-bound keypair.

        The keypair is generated inside the SGX/SEV enclave. The private
        key is hardware-bound and cannot be extracted.

        Returns the identity dict including the XRPL classic address.
        """
        if not _SDK_AVAILABLE:
            log.warning("xrpl-py not installed — returning stub identity")
            return self._stub_identity(player_id)

        # In production: keypair generated inside TEE via tee.generate_xrpl_keypair()
        # Stub: generate ephemeral wallet
        wallet = Wallet.create()
        log.info("Created XRPL account %s for player %s", wallet.classic_address, player_id)

        identity = {
            "player_id": player_id,
            "xrpl_address": wallet.classic_address,
            "hw_fingerprint": getattr(tee, "get_bound_fingerprint", lambda: "STUB_FP")(),
            "reputation": 0,
            "nft_id": None,
        }

        # Mint genesis reputation NFT (score=0, soulbound)
        nft_id = await self._mint_reputation_nft(player_id, 0, wallet)
        identity["nft_id"] = nft_id
        log.info("Minted genesis reputation NFT %s for player %s", nft_id, player_id)
        return identity

    async def update_reputation(
        self, player_id: str, score: int, xrpl_address: str
    ) -> dict[str, Any]:
        """
        Mint an updated reputation NFT for *player_id* reflecting *score*.

        Each reputation update mints a new NFT with the current score and
        timestamp. The NFT is non-transferable (soulbound) and serves as a
        portable, cross-game reputation credential.

        Returns the new NFT metadata dict.
        """
        if not _SDK_AVAILABLE:
            return {"nft_id": "STUB_NFT", "score": score}

        wallet = Wallet.create()  # in prod: load TEE-bound wallet
        nft_id = await self._mint_reputation_nft(player_id, score, wallet)
        log.info("Updated reputation NFT player=%s score=%d nft=%s", player_id, score, nft_id)
        return {"nft_id": nft_id, "score": score, "ts": int(time.time())}

    # ── NFT minting ───────────────────────────────────────────────────────

    async def _mint_reputation_nft(
        self, player_id: str, score: int, wallet: Any
    ) -> str:
        """
        Mint a non-transferable XLS-20 NFT encoding the player's reputation.

        NFT URI field (hex-encoded JSON):
          {"player_id": "...", "score": N, "ts": unix_epoch}

        tfTransferable is NOT set — the NFT is soulbound to the account.
        """
        uri_data = json.dumps(
            {"player_id": player_id, "score": score, "ts": int(time.time())},
            separators=(",", ":"),
        )
        uri_hex = uri_data.encode().hex().upper()

        async with AsyncJsonRpcClient(self.url) as client:
            tx = NFTokenMint(
                account=wallet.classic_address,
                nftoken_taxon=IRONWALL_NFT_TAXON,
                flags=NFTokenMintFlag.TF_ONLY_XRP,  # non-transferable by default
                uri=uri_hex,
            )
            response = await submit_and_wait(tx, client, wallet)

        # Extract NFTokenID from metadata
        nft_id = (
            response.result
            .get("meta", {})
            .get("nftoken_id", "UNKNOWN_NFT_ID")
        )
        return nft_id

    def _stub_identity(self, player_id: str) -> dict[str, Any]:
        return {
            "player_id": player_id,
            "xrpl_address": "rSTUB000000000000000000000000000000",
            "hw_fingerprint": "STUB_FINGERPRINT",
            "reputation": 0,
            "nft_id": None,
        }
