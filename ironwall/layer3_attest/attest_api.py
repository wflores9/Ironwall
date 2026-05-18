"""
ironwall.layer3_attest.attest_api
───────────────────────────────────
aiohttp HTTP server — receives ModuleManifest from the Rust launcher,
runs TEE verification on each module hash, and issues a session token.

Endpoints:
  POST /attest   — submit manifest, receive session token
  GET  /health   — liveness check

This is the Python side of the Rust ↔ Python handshake:
  [ironwall-launcher (Rust)] ──POST /attest──▶ [attest_api.py (Python)]
                                                       │
                                              TEEVerifier.verify_and_attest()
                                              RemoteAttestationBroker
                                                       │
                                              ◀── { status, session_token }

Run:
  python -m ironwall.layer3_attest.attest_api
  # or via Makefile: make run-broker
"""

from __future__ import annotations

import json
import os
from typing import Any

from aiohttp import web

from ironwall.core.logging import get_logger
from ironwall.layer2_signing.tee_verifier import TEEVerifier
from ironwall.layer3_attest.broker import RemoteAttestationBroker

log = get_logger("layer3.attest_api")

_broker = RemoteAttestationBroker()
_tee = TEEVerifier()

# In production: load from ModuleSigner records / CT log
# Map: sha3_256_hex → signature_record
_KNOWN_SIGNATURES: dict[str, dict[str, Any]] = {}


def load_signatures(path: str) -> None:
    """Load known module signature records from a JSON file."""
    with open(path) as f:
        records = json.load(f)
    for record in records:
        _KNOWN_SIGNATURES[record["mod_hash"]] = record
    log.info("Loaded %d signature records", len(_KNOWN_SIGNATURES))


# ── Request handlers ──────────────────────────────────────────────────────

async def handle_attest(request: web.Request) -> web.Response:
    """
    POST /attest

    Body (JSON): ModuleManifest from ironwall-launcher (Rust)
    Response:    AttestationResponse JSON
    """
    try:
        body = await request.json()
    except Exception:
        return _error_response("Invalid JSON body", 400)

    manifest = body.get("manifest", {})
    player_id = manifest.get("player_id", "unknown")
    modules = manifest.get("modules", [])
    sgx_quote = body.get("sgx_quote")

    log.info(
        "Attest request: player=%s modules=%d session=%s",
        player_id, len(modules), manifest.get("session_id", "?")
    )

    # ── Verify each module hash ───────────────────────────────────────
    banned_modules = []
    for module in modules:
        filename = module.get("filename", "?")
        mod_hash = module.get("sha3_256", "")

        if mod_hash in ("SKIPPED", "TOO_LARGE"):
            continue

        sig_record = _KNOWN_SIGNATURES.get(mod_hash)

        if sig_record is None:
            # Unknown hash — module not in CT log
            log.warning("Unknown module hash: %s (%s)", filename, mod_hash[:16])
            banned_modules.append(filename)
            continue

        # Verify signature record via TEEVerifier
        # In production: pass actual module bytes; here we trust the hash
        result = _tee.verify_and_attest(
            code=bytes.fromhex(mod_hash),  # stand-in; real impl reads the binary
            sig=sig_record,
        )
        if result.get("status") == "BANNED":
            log.warning("Module banned: %s reason=%s", filename, result.get("reason"))
            banned_modules.append(filename)

    if banned_modules:
        return web.json_response({
            "status": "BANNED",
            "reason": f"Banned modules detected: {banned_modules}",
            "banned_modules": banned_modules,
            "session_token": None,
            "tee_receipt": None,
        })

    # ── Build attestation dict for broker ─────────────────────────────
    attest = {
        "sgx_quote": sgx_quote or f"SIM_QUOTE_{manifest.get('manifest_hash', '')[:32]}",
        "verified": True,
    }

    token = await _broker.initialize_session(player_id, attest)

    if token is None:
        return web.json_response({
            "status": "DENIED",
            "reason": "TEE attestation failed",
            "session_token": None,
            "tee_receipt": None,
        }, status=403)

    log.info("Session token issued for player %s", player_id)
    return web.json_response({
        "status": "ATTESTED",
        "session_token": token,
        "tee_receipt": attest,
        "banned_modules": [],
        "reason": None,
    })


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — liveness probe."""
    return web.json_response({"status": "ok", "service": "ironwall-attest-api"})


# ── App factory ───────────────────────────────────────────────────────────

def build_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/attest", handle_attest)
    app.router.add_get("/health", handle_health)
    return app


def _error_response(msg: str, status: int) -> web.Response:
    return web.json_response({"error": msg}, status=status)


if __name__ == "__main__":
    host = os.environ.get("ATTEST_HOST", "127.0.0.1")
    port = int(os.environ.get("ATTEST_PORT", "8766"))
    log.info("Starting attest API on %s:%d", host, port)
    web.run_app(build_app(), host=host, port=port)
