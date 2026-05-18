"""
ironwall.layer4_xrpl
─────────────────────
XRPL integration layer — hardens Ironwall with a second independent ledger.

Components:
  DualAnchorRecorder   — commits match records to Hedera HCS + XRPL simultaneously
  XRPLMatchRecorder    — XRPL-only anchor via AccountSet + Memo
  XRPLEscrow           — native protocol-level escrow (no smart contract)
  XRPLPlayerIdentity   — device-bound XRPL accounts + XLS-20 reputation NFTs
  hooks/zk_verifier.ts — XLS-30 Hook: validates ZK proof hash before EscrowFinish

Why two ledgers:
  Hedera provides aBFT ordered consensus and wagering settlement.
  XRPL provides a second immutable anchor with a different consensus mechanism,
  native escrow with zero bytecode attack surface, and XLS-20 soulbound NFTs
  for portable cross-game reputation (compatible with Ward Protocol / XLS-66).
"""

from ironwall.layer4_xrpl.recorder import DualAnchorRecorder, XRPLMatchRecorder
from ironwall.layer4_xrpl.escrow import XRPLEscrow
from ironwall.layer4_xrpl.identity import XRPLPlayerIdentity

__all__ = [
    "DualAnchorRecorder",
    "XRPLMatchRecorder",
    "XRPLEscrow",
    "XRPLPlayerIdentity",
]
