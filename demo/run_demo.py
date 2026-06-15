#!/usr/bin/env python3
"""
demo/run_demo.py — Ironwall end-to-end demo (SIM mode)
────────────────────────────────────────────────────────

Fully automated. Demonstrates the real protocol trust chain without
requiring a game engine, SGX hardware, or any account setup beyond
internet access (uses the public XRPL testnet faucet).

Flow:
  1. Generate a developer keypair, sign a "game module" (synthetic bytes).
  2. Simulate a match: generate input events, build an InputMerkleTree.
  3. Run TEEVerifier.verify_and_attest() in SIM mode — produces an
     attestation receipt (sgx_quote = "SIM_QUOTE_...").
  4. Build the match fingerprint (merkle_root + receipt_hash) and anchor
     it to XRPL testnet via a freshly-funded faucet wallet.
  5. Write audit.json (Merkle leaves) and receipt.json (attestation
     receipt) — the same files `ironwall-verify` consumes.
  6. Print the XRPL tx hash and the exact `ironwall-verify` commands to
     run — once for a clean PASS, once after tampering for a FAIL.

Run:
    python demo/run_demo.py

Output:
    demo/audit.json
    demo/receipt.json
    demo/audit_tampered.json   (for the FAIL demonstration)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path

from ironwall.layer2_signing.signer import ModuleSigner
from ironwall.layer2_signing.tee_verifier import TEEVerifier, register_public_key
from ironwall.merkle_audit.tree import InputMerkleTree
from ironwall.layer4_xrpl.recorder import XRPLMatchRecorder

DEMO_DIR = Path(__file__).parent
CT_LOG_PATH = DEMO_DIR / "ct_log.jsonl"

_GREEN = "\033[92m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _step(n: int, total: int, title: str) -> None:
    print()
    print(f"{_BOLD}[{n}/{total}] {title}{_RESET}")
    print("─" * 50)


async def main() -> None:
    # Fresh CT log per demo run.
    os.environ["IRONWALL_CT_LOG_PATH"] = str(CT_LOG_PATH)
    if CT_LOG_PATH.exists():
        CT_LOG_PATH.unlink()

    print(f"{_BOLD}{_CYAN}IRONWALL END-TO-END DEMO (SIM mode){_RESET}")
    print("Launch → Attest → Capture → Anchor (XRPL testnet) → Verify")

    # ── Step 1: developer keypair + sign the "game module" ─────────────
    _step(1, 6, "Sign game module (Layer 2 — ECDSA P-256 + CT log)")

    priv_pem, pub_pem = ModuleSigner.generate_key_pem()
    signer = ModuleSigner(priv_pem)

    dev_id = "studio-demo-001"
    register_public_key(dev_id, pub_pem)

    # Synthetic "game binary" — in production this is the real launcher/exe.
    game_module = b"IRONWALL_DEMO_GAME_BINARY_v1.0" + os.urandom(256)

    sig_record = signer.sign_module(game_module, dev_id)
    print(f"  dev_id    : {dev_id}")
    print(f"  mod_hash  : {sig_record['mod_hash'][:32]}…")
    print(f"  ct_anchor : {sig_record['ct_anchor'][:32]}…")

    # ── Step 2: simulate a match — input capture + Merkle tree ─────────
    _step(2, 6, "Simulate match input capture (Merkle audit tree)")

    session_key = os.urandom(32)
    tree = InputMerkleTree()

    players = ["player_alice", "player_bob"]
    n_events = 40
    base_ts = int(time.time() * 1e9)

    for i in range(n_events):
        player = players[i % 2]
        # Synthetic input: keypress/mouse-move payload
        data = f"{player}:input_event_{i}".encode()
        ts = base_ts + i * 16_666_667  # ~60Hz tick
        tree.record_input(ts=ts, data=data, session_key=session_key)

    merkle_root = tree.root()
    print(f"  players     : {', '.join(players)}")
    print(f"  input events: {n_events}")
    print(f"  merkle_root : {merkle_root[:32]}…")

    # ── Step 3: TEE attestation (SIM mode) ─────────────────────────────
    _step(3, 6, "Runtime TEE attestation (Layer 3 — SIM mode)")

    verifier = TEEVerifier()
    receipt = verifier.verify_and_attest(game_module, sig_record)

    if not receipt.get("verified"):
        print(f"  {_RED}✗ ATTESTATION FAILED: {receipt}{_RESET}")
        return

    print(f"  status    : {receipt['status']}")
    print(f"  sgx_quote : {receipt['sgx_quote']}")
    print(f"  verified  : {receipt['verified']}")

    # ── Step 4: build fingerprint + anchor to XRPL testnet ─────────────
    _step(4, 6, "Anchor match record to XRPL testnet")

    match_id = f"demo-match-{int(time.time())}"
    end_time = int(time.time() * 1000)

    result = {
        "id": match_id,
        "input_merkle_root": merkle_root,
        "end_time": end_time,
    }

    print("  Requesting funded wallet from XRPL testnet faucet…")
    try:
        from xrpl.asyncio.wallet import generate_faucet_wallet
        from xrpl.asyncio.clients import AsyncJsonRpcClient

        faucet_client = AsyncJsonRpcClient(XRPLMatchRecorder.TESTNET)
        wallet = await generate_faucet_wallet(faucet_client, debug=False)
        print(f"  wallet      : {wallet.classic_address}")
    except Exception as exc:
        print(f"  {_RED}✗ Could not fund testnet wallet: {exc}{_RESET}")
        print(f"  {_CYAN}Falling back to STUB anchor (no real XRPL tx).{_RESET}")
        wallet = None

    recorder = XRPLMatchRecorder(wallet, network="testnet")
    anchor = await recorder.commit_match_record(result, receipt)

    tx_hash = anchor.get("tx_hash", "STUB_XRPL_TX")
    fingerprint = anchor["fingerprint"]["data"]

    print(f"  tx_hash     : {tx_hash}")
    print(f"  match_id    : {fingerprint['match_id']}")
    print(f"  receipt_hash: {fingerprint['receipt_hash'][:32]}…")

    # ── Step 5: write verification record files ────────────────────────
    _step(5, 6, "Write verification artifacts")

    record_path = DEMO_DIR / "match_record.json"
    record_tampered_path = DEMO_DIR / "match_record_tampered.json"
    audit_path = DEMO_DIR / "audit.json"
    receipt_path = DEMO_DIR / "receipt.json"

    # ironwall-verify (current main) expects a record JSON file. The XRPL
    # fingerprint shape ({"fingerprint": {"data": {...}}}) is one of the
    # formats it recognises directly.
    record = {"fingerprint": {"data": dict(fingerprint)}}
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True))

    # Tampered version — current ironwall-verify validates record structure
    # and field formats (hex64 lengths, required keys), not on-chain Merkle
    # recomputation. Demonstrate FAIL via a malformed merkle_root, which the
    # structural check rejects.
    tampered_fingerprint = dict(fingerprint)
    tampered_fingerprint["merkle_root"] = "not_a_valid_merkle_root"
    record_tampered = {"fingerprint": {"data": tampered_fingerprint}}
    record_tampered_path.write_text(json.dumps(record_tampered, indent=2, sort_keys=True))

    # Also keep the raw Merkle leaves + receipt for anyone doing a full
    # from-scratch audit (not consumed by ironwall-verify directly).
    audit_path.write_text(json.dumps({"leaves": tree.leaves}, indent=2))
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True))

    print(f"  wrote {record_path}            (verify input — clean)")
    print(f"  wrote {record_tampered_path}   (verify input — tampered merkle_root)")
    print(f"  wrote {audit_path}              (raw Merkle leaves, for audit)")
    print(f"  wrote {receipt_path}            (TEE attestation receipt)")

    # ── Step 6: run ironwall-verify — PASS, then FAIL ──────────────────
    _step(6, 6, "Independent verification (ironwall-verify)")

    print(f"  {_BOLD}Run 1 — clean record (expect PASS):{_RESET}")
    print(f"    $ ironwall-verify {record_path}")
    print()
    rc1, out1 = _run_verify_cli(record_path)
    print(f"    {out1}")
    print(f"  → exit code {rc1} {'(PASS)' if rc1 == 0 else '(FAIL)'}")

    print()
    print(f"  {_BOLD}Run 2 — tampered record, corrupted merkle_root (expect FAIL):{_RESET}")
    print(f"    $ ironwall-verify {record_tampered_path}")
    print()
    rc2, out2 = _run_verify_cli(record_tampered_path)
    print(f"    {out2}")
    print(f"  → exit code {rc2} {'(PASS)' if rc2 == 0 else '(FAIL)'}")

    print()
    print("═" * 50)
    if rc1 == 0 and rc2 != 0:
        print(f"{_BOLD}{_GREEN}DEMO COMPLETE — protocol behaved correctly.{_RESET}")
        print("  Clean record verified.  Tampered record rejected.")
    else:
        print(f"{_BOLD}{_RED}DEMO RESULT UNEXPECTED — see output above.{_RESET}")

    if tx_hash != "STUB_XRPL_TX":
        print(f"\n  XRPL tx (testnet): {tx_hash}")
        print(f"  Explorer: https://testnet.xrpl.org/transactions/{tx_hash}")
    print()


def _run_verify_cli(record_path: Path) -> tuple[int, str]:
    """Run `ironwall-verify <record.json>` as a subprocess, return (exit_code, output)."""
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "ironwall.cli.verify", str(record_path)],
        capture_output=True,
        text=True,
    )
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode, out


if __name__ == "__main__":
    asyncio.run(main())
