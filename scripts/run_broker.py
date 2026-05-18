"""
scripts/run_broker.py
──────────────────────
One-shot broker startup script. Handles venv creation, dependency install,
and service launch. Works on Windows and Linux.

Usage:
    python scripts/run_broker.py
    python scripts/run_broker.py --port 8766 --signatures signatures.json

This starts:
    ironwall.layer3_attest.attest_api  — POST /attest, GET /health
    Listening on http://127.0.0.1:8766

The Rust launcher connects to this on startup.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
VENV_DIR = REPO_ROOT / ".venv"
REQUIRED_PACKAGES = [
    "aiohttp>=3.9",
    "cryptography>=42",
    "pyjwt>=2.8",
]


def banner():
    print("""
╔══════════════════════════════════════════════╗
║   IRONWALL — TEE Attestation Broker          ║
║   POST /attest  ·  GET /health               ║
╚══════════════════════════════════════════════╝
""")


def ensure_venv():
    """Create venv if it doesn't exist."""
    if not VENV_DIR.exists():
        print(f"Creating virtualenv at {VENV_DIR}...")
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)
        print("  [OK] venv created")
    else:
        print(f"  [OK] venv exists at {VENV_DIR}")


def python_in_venv() -> str:
    """Return path to Python interpreter inside venv."""
    if sys.platform == "win32":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def ensure_deps():
    """Install required packages into venv."""
    py = python_in_venv()
    print("Installing dependencies...")
    subprocess.run(
        [py, "-m", "pip", "install", "--quiet", "--upgrade"] + REQUIRED_PACKAGES,
        check=True,
    )
    # Install ironwall itself in editable mode
    subprocess.run(
        [py, "-m", "pip", "install", "--quiet", "-e", str(REPO_ROOT)],
        check=True,
    )
    print("  [OK] dependencies installed")


def run_broker(host: str, port: int, signatures: str | None, sgx_mode: str):
    """Launch the attestation API."""
    py = python_in_venv()

    env = os.environ.copy()
    env["ATTEST_HOST"] = host
    env["ATTEST_PORT"] = str(port)
    env["SGX_MODE"] = sgx_mode
    env["SESSION_SECRET"] = env.get(
        "SESSION_SECRET",
        "ironwall_dev_secret_32bytes_xxxxx"  # dev default — override in prod
    )

    if signatures:
        env["IRONWALL_SIGNATURES"] = signatures

    cmd = [py, "-m", "ironwall.layer3_attest.attest_api"]

    print(f"\nStarting broker on http://{host}:{port}")
    print(f"SGX_MODE: {sgx_mode}")
    if signatures:
        print(f"Signatures: {signatures}")
    print("\nPress Ctrl+C to stop.\n")

    try:
        subprocess.run(cmd, env=env, cwd=str(REPO_ROOT), check=True)
    except KeyboardInterrupt:
        print("\nBroker stopped.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Broker exited with code {e.returncode}")
        sys.exit(e.returncode)


def main():
    parser = argparse.ArgumentParser(
        description="Start the Ironwall TEE attestation broker"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8766, help="Bind port (default: 8766)")
    parser.add_argument("--signatures", help="Path to JSON file with known module hashes")
    parser.add_argument("--sgx-mode", default="SIM", choices=["SIM", "HW"],
                        help="SGX mode: SIM (default) or HW")
    parser.add_argument("--skip-setup", action="store_true",
                        help="Skip venv/dep setup (use if already installed)")
    args = parser.parse_args()

    banner()

    if not args.skip_setup:
        ensure_venv()
        ensure_deps()

    run_broker(args.host, args.port, args.signatures, args.sgx_mode)


if __name__ == "__main__":
    main()
