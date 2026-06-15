"""
ironwall.layer1_thinclient.client
──────────────────────────────────
Thin client: captures raw input, signs it with the session key, streams it to
the game server over WebSocket, and renders the returned H.264 video frame.

NO game logic lives here. Any PR that moves game state computation client-side
will be rejected.

Open issues / good-first tasks:
  #112 — Adaptive bitrate control for video encoder
  #118 — Controller input normalisation (Xbox / PS5 / Switch)
  #89  — Rust rewrite of capture_input() for sub-1ms latency  [bounty: 500 HBAR]
  #134 — IPv6 dual-stack support for WebSocket transport
"""

from __future__ import annotations

import asyncio
import struct
from dataclasses import dataclass
from time import time_ns
from typing import Optional

import aiohttp

from ironwall.core.crypto import hmac_sign
from ironwall.core.logging import get_logger
from ironwall.layer1_thinclient.controller import (
    RawControllerState,
    normalize_controller_state,
    serialize_controller_input,
)

log = get_logger("layer1.client")

# ── Wire format ────────────────────────────────────────────────────────────
# InputPacket: seq(8) | timestamp_ns(8) | hmac(32) | payload(N)
_HEADER = struct.Struct(">QQ32s")  # big-endian: seq, ts, hmac


@dataclass
class InputPacket:
    seq: int
    timestamp: int        # nanoseconds
    payload: bytes        # raw input bytes
    hmac: bytes           # HMAC-SHA3-256 of payload under session_key


def pack(pkt: InputPacket) -> bytes:
    header = _HEADER.pack(pkt.seq, pkt.timestamp, pkt.hmac)
    return header + pkt.payload


def unpack(data: bytes) -> InputPacket:
    seq, ts, hmac_bytes = _HEADER.unpack_from(data)
    payload = data[_HEADER.size:]
    return InputPacket(seq=seq, timestamp=ts, payload=payload, hmac=hmac_bytes)


# ── Input capture (stub — replace with platform impl or Rust extension) ────
async def capture_input() -> bytes:
    """
    Capture one frame of raw input (mouse delta, keys, controller).
    Returns a compact binary blob — format TBD by platform layer.

    TODO #89: Rust rewrite for sub-1ms latency.
    Platform integrations should pass raw gamepad state through
    normalize_controller_state() before serialising it into this payload.
    """
    await asyncio.sleep(1 / 60)  # 60 Hz polling stub
    normalized = normalize_controller_state(RawControllerState(kind="xbox"))
    return serialize_controller_input(normalized)


# ── Frame rendering (stub) ─────────────────────────────────────────────────
def render_frame(frame: bytes) -> None:
    """Decode H.264 frame and display it. Stub — integrate opencv or platform SDK."""
    # TODO #112: add adaptive bitrate negotiation here
    pass


# ── ThinClient ─────────────────────────────────────────────────────────────
class ThinClient:
    """
    Thin client session.

    Args:
        session_key: 32-byte shared secret negotiated during attestation.
        server_url:  WebSocket URL of the game server edge node.
    """

    def __init__(self, session_key: bytes, server_url: str) -> None:
        if len(session_key) != 32:
            raise ValueError("session_key must be exactly 32 bytes")
        self.session_key = session_key
        self.server_url = server_url
        self.seq: int = 0           # monotonic — prevents replay attacks
        self.running: bool = False

    async def run(self) -> None:
        self.running = True
        log.info("ThinClient connecting to %s", self.server_url)

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(self.server_url) as ws:
                log.info("WebSocket open — starting input loop")
                while self.running:
                    raw = await capture_input()

                    pkt = InputPacket(
                        seq=self.seq,
                        timestamp=time_ns(),
                        payload=raw,
                        hmac=hmac_sign(raw, self.session_key),
                    )
                    await ws.send_bytes(pack(pkt))
                    self.seq += 1

                    msg = await ws.receive()
                    if msg.type == aiohttp.WSMsgType.BINARY:
                        render_frame(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                        log.warning("WebSocket closed: %s", msg)
                        break

        self.running = False
        log.info("ThinClient session ended (seq=%d)", self.seq)

    def stop(self) -> None:
        self.running = False
