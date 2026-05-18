"""
scripts/sign_modules.py
────────────────────────
Sign all DLLs in a game directory with ModuleSigner and output
known_hashes.json — the file the Rust launcher uses to verify modules.

This is the publisher-side workflow (run by Activision / game dev):
  1. Generate a signing keypair (one time)
  2. Sign all DLLs at build time → known_hashes.json + ct_log.jsonl
  3. Ship known_hashes.json alongside the game (or serve from CDN)
  4. The launcher fetches known_hashes.json on startup and passes it to
     the TEE broker for verification

Usage:
    # Generate a new keypair (first time only)
    python scripts/sign_modules.py --generate-key --key-out signing_key.pem

    # Sign all DLLs in a game directory
    python scripts/sign_modules.py \\
        --game-dir "C:\\cod25" \\
        --key signing_key.pem \\
        --dev-id "activision-cod25" \\
        --out known_hashes.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ironwall.layer2_signing.signer import ModuleSigner

MODULE_EXTENSIONS = {".dll", ".so", ".dylib"}


def find_modules(game_dir: Path) -> list[Path]:
    modules = []
    for path in game_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in MODULE_EXTENSIONS:
            modules.append(path)
    return sorted(modules)


def sign_all(game_dir: Path, key_pem: bytes, dev_id: str) -> list[dict]:
    signer = ModuleSigner(key_pem)
    modules = find_modules(game_dir)

    if not modules:
        print(f"[WARN] No modules found in {game_dir}")
        return []

    print(f"Found {len(modules)} modules in {game_dir}")
    records = []

    for i, path in enumerate(modules, 1):
        code = path.read_bytes()
        record = signer.sign_module(code, dev_id)
        record["filename"] = path.name
        record["path"] = str(path)
        record["size_bytes"] = len(code)
        records.append(record)
        print(f"  [{i:3d}/{len(modules)}] {path.name} → {record['mod_hash'][:16]}…")

    return records


def build_known_hashes(records: list[dict]) -> dict[str, str]:
    """Build filename → sha3_256 map for the Rust launcher."""
    return {r["filename"]: r["mod_hash"] for r in records}


def main():
    parser = argparse.ArgumentParser(description="Sign game modules with ModuleSigner")
    parser.add_argument("--game-dir", help="Game installation directory")
    parser.add_argument("--key", help="Path to PEM private key file")
    parser.add_argument("--dev-id", default="ironwall-publisher",
                        help="Developer ID (e.g. 'activision-cod25')")
    parser.add_argument("--out", default="known_hashes.json",
                        help="Output path for known_hashes.json")
    parser.add_argument("--generate-key", action="store_true",
                        help="Generate a new ECDSA P-256 keypair and exit")
    parser.add_argument("--key-out", default="signing_key.pem",
                        help="Output path for generated private key")
    args = parser.parse_args()

    # ── Key generation mode ───────────────────────────────────────────
    if args.generate_key:
        priv_pem, pub_pem = ModuleSigner.generate_key_pem()
        priv_path = Path(args.key_out)
        pub_path = priv_path.with_suffix(".pub.pem")
        priv_path.write_bytes(priv_pem)
        pub_path.write_bytes(pub_pem)
        print(f"[OK] Private key: {priv_path}")
        print(f"[OK] Public key:  {pub_path}")
        print(f"\nKEEP {priv_path} SECRET — do not commit to git.")
        print(f"Distribute {pub_path} to the TEE broker.")
        return

    # ── Signing mode ──────────────────────────────────────────────────
    if not args.game_dir or not args.key:
        parser.error("--game-dir and --key are required for signing")

    game_dir = Path(args.game_dir)
    if not game_dir.exists():
        print(f"[ERROR] Game directory not found: {game_dir}")
        sys.exit(1)

    key_path = Path(args.key)
    if not key_path.exists():
        print(f"[ERROR] Key file not found: {key_path}")
        print(f"Generate one with: python scripts/sign_modules.py --generate-key")
        sys.exit(1)

    key_pem = key_path.read_bytes()

    print(f"\n── Signing modules ──────────────────────────────────")
    print(f"Game dir:  {game_dir}")
    print(f"Dev ID:    {args.dev_id}")
    print(f"Key:       {key_path}")
    print()

    records = sign_all(game_dir, key_pem, args.dev_id)

    # Save full signature records (for broker)
    records_path = Path(args.out).with_suffix("") .with_suffix(".signatures.json")
    records_path.write_text(json.dumps(records, indent=2))
    print(f"\n[OK] Full signature records: {records_path}")

    # Save known_hashes.json (for Rust launcher)
    known = build_known_hashes(records)
    out_path = Path(args.out)
    out_path.write_text(json.dumps(known, indent=2))
    print(f"[OK] Known hashes (launcher): {out_path}")
    print(f"\nSigned {len(records)} modules.")
    print(f"\nNext steps:")
    print(f"  1. Start broker:   python scripts/run_broker.py --signatures {records_path}")
    print(f"  2. Run launcher:   ironwall-launcher.exe --game-dir \"{game_dir}\" --known-hashes {out_path} ...")


if __name__ == "__main__":
    main()
