"""
ironwall.layer1_thinclient.server
──────────────────────────────────
Game server simulation loop. Runs on Activision edge nodes.

Trust model: everything client-side is adversarial. Game state NEVER leaves
this module. extract_pov() is the fog-of-war boundary — see DANGER note below.

Security-critical PRs (extract_pov, HMAC verification) require two maintainer
reviews. See CONTRIBUTING.md.

Open issues:
  #97  — Security audit: extract_pov() speculative visibility leak  [bounty: 1000 HBAR]
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from aiohttp import web

from ironwall.core.crypto import hmac_verify
from ironwall.core.logging import get_logger
from ironwall.layer1_thinclient.client import InputPacket, unpack
from ironwall.merkle_audit.tree import InputMerkleTree

log = get_logger("layer1.server")


class InvalidInputError(Exception):
    def __init__(self, player_id: str, reason: str) -> None:
        super().__init__(f"[{player_id}] {reason}")
        self.player_id = player_id
        self.reason = reason


# ── Stub world / renderer (replace with real game engine) ─────────────────
class _World:
    """Stub physics/game-state simulation. Replace with bullet3/custom engine."""

    def step(self, player_id: str, input_bytes: bytes) -> dict[str, Any]:
        """Apply *input_bytes* to the world and return the new authoritative state."""
        return {"entities": [], "player_id": player_id}  # stub


class _Renderer:
    """Stub H.264 frame encoder. Replace with real encoder (ffmpeg, nvenc, etc.)."""

    def encode_h264(self, pov: dict[str, Any]) -> bytes:
        return b"\x00" * 1024  # stub — one blank frame


def extract_pov(state: dict[str, Any], player_id: str) -> dict[str, Any]:
    """
    DANGER — THIS IS THE FOG-OF-WAR BOUNDARY.

    Must NEVER include entity positions outside the requesting player's
    visibility cone. Any information leak here is a cheat-enabling bug.

    All PRs touching this function require TWO maintainer reviews.
    See issue #97 for the open speculative-visibility audit.
    """
    # TODO #97: audit against speculative visibility leaks
    return {"player_id": player_id, "visible_entities": []}  # stub


# ── GameServer ────────────────────────────────────────────────────────────
class GameServer:
    """
    Authoritative game server.

    Holds game state, session keys, and a per-player Merkle tree.
    Streams signed, attested video frames back to each ThinClient.
    """

    def __init__(self) -> None:
        self.world = _World()
        self.renderer = _Renderer()
        self.session_keys: dict[str, bytes] = {}  # player_id → 32-byte key
        self.merkle: dict[str, InputMerkleTree] = {}

    def register_player(self, player_id: str, session_key: bytes) -> None:
        """Called by RemoteAttestationBroker after a successful attestation."""
        self.session_keys[player_id] = session_key
        self.merkle[player_id] = InputMerkleTree()
        log.info("Registered player %s", player_id)

    async def process_tick(self, player_id: str, pkt: InputPacket) -> bytes:
        """
        One server tick for *player_id*:
          1. Verify HMAC — reject tampered inputs immediately.
          2. Simulate — game state NEVER leaves this function.
          3. Render player-POV only — fog-of-war enforced by extract_pov().
          4. Accumulate input into the match Merkle tree.
        Returns the H.264-encoded frame bytes.
        """
        if player_id not in self.session_keys:
            raise InvalidInputError(player_id, "UNKNOWN_PLAYER")

        # 1. HMAC verification
        if not hmac_verify(pkt.payload, pkt.hmac, self.session_keys[player_id]):
            raise InvalidInputError(player_id, "HMAC_FAIL")

        # 2. Simulate — authoritative, server-side only
        new_state = self.world.step(player_id, pkt.payload)

        # 3. Render — fog-of-war boundary
        pov = extract_pov(new_state, player_id)
        frame = self.renderer.encode_h264(pov)

        # 4. Accumulate into Merkle tree
        self.merkle[player_id].record_input(
            ts=pkt.timestamp,
            data=pkt.payload,
            session_key=self.session_keys[player_id],
        )

        return frame

    def get_match_merkle_root(self, player_id: str) -> str:
        """Return the Merkle root for *player_id*'s inputs. Called at match end."""
        return self.merkle[player_id].root()

    # ── aiohttp WebSocket handler ─────────────────────────────────────────
    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        player_id = request.match_info.get("player_id", "unknown")
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        log.info("WebSocket open — player %s", player_id)

        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                try:
                    pkt = unpack(msg.data)
                    frame = await self.process_tick(player_id, pkt)
                    await ws.send_bytes(frame)
                except InvalidInputError as exc:
                    log.warning("Dropping connection: %s", exc)
                    await ws.close(code=4001, message=exc.reason.encode())
                    break
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

        log.info("WebSocket closed — player %s", player_id)
        return ws

    def build_app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/ws/{player_id}", self.ws_handler)
        return app


def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    server = GameServer()
    app = server.build_app()
    log.info("GameServer listening on %s:%d", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
