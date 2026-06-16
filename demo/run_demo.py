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
  4. Dual-anchor: commit to Hedera HCS + XRPL testnet via DualAnchorRecorder.
     Falls back to XRPL-only (with warning) if Hedera env vars are missing.
  5. Write match_record.json and match_record_tampered.json for ironwall-verify.
  6. Run ironwall-verify on both — expect PASS then FAIL.

Run:
    python demo/run_demo.py

Environment (optional — load via .env or export directly):
    HEDERA_OPERATOR_ID   — 0.0.XXXXXX
    HEDERA_OPERATOR_KEY  — ED25519 private key hex
    IRONWALL_TOPIC_ID    — 0.0.YYYYYY  (HCS match-record topic)
    HEDERA_NETWORK       — testnet | mainnet  (default: testnet)

Output:
    demo/match_record.json
    demo/match_record_tampered.json
    demo/audit.json
    demo/receipt.json
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from pathlib import Path

from ironwall.core.crypto import sha3_256_hex
from ironwall.layer2_signing.signer import ModuleSigner
from ironwall.layer2_signing.tee_verifier import TEEVerifier, register_public_key
from ironwall.merkle_audit.tree import InputMerkleTree
from ironwall.layer4_hedera.recorder import HederaMatchRecorder
from ironwall.layer4_xrpl.recorder import XRPLMatchRecorder, DualAnchorRecorder

DEMO_DIR = Path(__file__).parent
CT_LOG_PATH = DEMO_DIR / "ct_log.jsonl"

_GREEN = "\033[92m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_YELLOW = "\033[93m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _step(n: int, total: int, title: str) -> None:
    print()
    print(f"{_BOLD}[{n}/{total}] {title}{_RESET}")
    print("─" * 50)


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore[import]
        load_dotenv()
    except ImportError:
        pass  # python-dotenv not installed; rely on os.environ


class _StubHederaRecorder:
    """Minimal stand-in for HederaMatchRecorder when env vars are absent."""
    async def commit_match_record(self, result: dict, attest: dict) -> dict:
        return {"consensus_timestamp": "STUB", "record": {}}


async def _build_hedera_recorder() -> tuple[object, bool]:
    """
    Attempt to build a HederaMatchRecorder from env vars.
    Returns (recorder, is_live). Falls back to _StubHederaRecorder when
    env vars are missing (avoids constructing HederaMatchRecorder with an
    invalid topic_id that the JVM-backed SDK would reject).
    """
    op_id = os.environ.get("HEDERA_OPERATOR_ID", "")
    op_key = os.environ.get("HEDERA_OPERATOR_KEY", "")
    topic_id = os.environ.get("IRONWALL_TOPIC_ID", "")

    if not (op_id and op_key and topic_id):
        missing = [v for v, k in [
            ("HEDERA_OPERATOR_ID", op_id),
            ("HEDERA_OPERATOR_KEY", op_key),
            ("IRONWALL_TOPIC_ID", topic_id),
        ] if not k]
        print(f"  {_YELLOW}⚠ Hedera env vars missing ({', '.join(missing)}) — HCS anchor will stub{_RESET}")
        return _StubHederaRecorder(), False

    try:
        from ironwall.core.hedera import build_hedera_client
        client = build_hedera_client(operator_id=op_id, operator_key=op_key)
        print(f"  hedera_op : {op_id}")
        print(f"  topic_id  : {topic_id}")
        return HederaMatchRecorder(client=client, topic_id=topic_id), True
    except Exception as exc:
        print(f"  {_YELLOW}⚠ Could not build Hedera client: {exc} — HCS anchor will stub{_RESET}")
        return _StubHederaRecorder(), False


async def main() -> None:
    _try_load_dotenv()

    # Fresh CT log per demo run.
    os.environ["IRONWALL_CT_LOG_PATH"] = str(CT_LOG_PATH)
    if CT_LOG_PATH.exists():
        CT_LOG_PATH.unlink()

    print(f"{_BOLD}{_CYAN}IRONWALL END-TO-END DEMO (SIM mode){_RESET}")
    print("Launch → Attest → Capture → Dual-Anchor (Hedera HCS + XRPL) → Verify")

    # ── Step 1: developer keypair + sign the "game module" ─────────────
    _step(1, 6, "Sign game module (Layer 2 — ECDSA P-256 + CT log)")

    priv_pem, pub_pem = ModuleSigner.generate_key_pem()
    signer = ModuleSigner(priv_pem)

    dev_id = "studio-demo-001"
    register_public_key(dev_id, pub_pem)

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

    # ── Step 4: dual-anchor to Hedera HCS + XRPL testnet ───────────────
    _step(4, 6, "Dual-anchor match record (Hedera HCS + XRPL testnet)")

    match_id = f"demo-match-{int(time.time())}"
    end_time = int(time.time() * 1000)

    # outcome_hash: SHA3-256 of sorted player list + merkle root (privacy-preserving)
    outcome_hash = sha3_256_hex(
        json.dumps({"players": sorted(players), "merkle_root": merkle_root}, sort_keys=True).encode()
    )

    result = {
        "id": match_id,
        "player_ids": players,
        "outcome_hash": outcome_hash,
        "input_merkle_root": merkle_root,
        "end_time": end_time,
    }

    # Hedera recorder
    print("  Building Hedera HCS recorder…")
    hedera_recorder, hedera_live = await _build_hedera_recorder()

    # XRPL faucet wallet
    print("  Requesting funded wallet from XRPL testnet faucet…")
    try:
        from xrpl.asyncio.wallet import generate_faucet_wallet
        from xrpl.asyncio.clients import AsyncJsonRpcClient

        faucet_client = AsyncJsonRpcClient(XRPLMatchRecorder.TESTNET)
        wallet = await generate_faucet_wallet(faucet_client, debug=False)
        print(f"  xrpl_wallet : {wallet.classic_address}")
    except Exception as exc:
        print(f"  {_YELLOW}⚠ Could not fund testnet wallet: {exc} — XRPL anchor will stub{_RESET}")
        wallet = None

    xrpl_recorder = XRPLMatchRecorder(wallet, network="testnet")
    dual = DualAnchorRecorder(hedera_recorder, xrpl_recorder)

    anchors = await dual.commit(result, receipt)

    hedera_anchor = anchors["hedera"]
    xrpl_anchor = anchors["xrpl"]
    fingerprint = xrpl_anchor["fingerprint"]["data"]

    hedera_ts = hedera_anchor.get("consensus_timestamp", "STUB")
    xrpl_tx = xrpl_anchor.get("tx_hash", "STUB_XRPL_TX")

    print()
    print(f"  {'✓' if hedera_live else '~'} Hedera consensus_timestamp : {hedera_ts}")
    print(f"  {'✓' if wallet else '~'} XRPL tx_hash              : {xrpl_tx}")
    print(f"  match_id                   : {fingerprint['match_id']}")
    print(f"  receipt_hash               : {fingerprint['receipt_hash'][:32]}…")

    if not hedera_live and wallet is None:
        print(f"  {_YELLOW}Both anchors in stub mode — set env vars for live anchoring.{_RESET}")
    elif not hedera_live:
        print(f"  {_YELLOW}Hedera HCS stub — set HEDERA_OPERATOR_ID / KEY / IRONWALL_TOPIC_ID for live.{_RESET}")

    # ── Step 5: write verification record files ────────────────────────
    _step(5, 6, "Write verification artifacts")

    record_path = DEMO_DIR / "match_record.json"
    record_tampered_path = DEMO_DIR / "match_record_tampered.json"
    audit_path = DEMO_DIR / "audit.json"
    receipt_path = DEMO_DIR / "receipt.json"

    record = {"fingerprint": {"data": dict(fingerprint)}}
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True))

    tampered_fingerprint = dict(fingerprint)
    tampered_fingerprint["merkle_root"] = "not_a_valid_merkle_root"
    record_tampered = {"fingerprint": {"data": tampered_fingerprint}}
    record_tampered_path.write_text(json.dumps(record_tampered, indent=2, sort_keys=True))

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

    if xrpl_tx != "STUB_XRPL_TX":
        print(f"\n  XRPL tx (testnet): {xrpl_tx}")
        print(f"  Explorer: https://testnet.xrpl.org/transactions/{xrpl_tx}")
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
