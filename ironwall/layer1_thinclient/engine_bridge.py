"""Engine-facing input bridge helpers for Unity and Unreal samples."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from time import time_ns
from typing import Any


class EngineKind(StrEnum):
    UNITY = "unity"
    UNREAL = "unreal"


@dataclass(frozen=True)
class EngineInputEvent:
    """Canonical input event emitted by a game-engine integration."""

    engine: EngineKind | str
    player_id: str
    sequence: int
    actions: dict[str, Any]
    timestamp_ns: int = field(default_factory=time_ns)

    def to_payload(self) -> dict[str, Any]:
        engine = self.engine if isinstance(self.engine, EngineKind) else EngineKind(self.engine)
        if not self.player_id:
            raise ValueError("player_id is required")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        if not isinstance(self.actions, dict):
            raise ValueError("actions must be an object")

        return {
            "engine": engine.value,
            "player_id": self.player_id,
            "sequence": self.sequence,
            "timestamp_ns": self.timestamp_ns,
            "actions": self.actions,
        }


def serialize_engine_input(event: EngineInputEvent) -> bytes:
    """Return deterministic bytes suitable for InputPacket.payload."""
    return json.dumps(event.to_payload(), separators=(",", ":"), sort_keys=True).encode()


def build_engine_input(
    *,
    engine: EngineKind | str,
    player_id: str,
    sequence: int,
    actions: dict[str, Any],
    timestamp_ns: int | None = None,
) -> bytes:
    """Convenience wrapper used by local engine bridge adapters."""
    event = EngineInputEvent(
        engine=engine,
        player_id=player_id,
        sequence=sequence,
        timestamp_ns=time_ns() if timestamp_ns is None else timestamp_ns,
        actions=actions,
    )
    return serialize_engine_input(event)
