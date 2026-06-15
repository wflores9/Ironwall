"""Controller input normalisation for Xbox, PlayStation, and Switch pads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable


class ControllerKind(StrEnum):
    """Supported controller families."""

    XBOX = "xbox"
    PS5 = "ps5"
    SWITCH = "switch"


@dataclass(frozen=True)
class RawControllerState:
    """Raw gamepad state from a platform capture layer."""

    kind: ControllerKind | str
    left_x: int = 0
    left_y: int = 0
    right_x: int = 0
    right_y: int = 0
    left_trigger: int = 0
    right_trigger: int = 0
    buttons: Iterable[str] = ()


@dataclass(frozen=True)
class NormalizedControllerInput:
    """Canonical controller payload used by the thin-client wire format."""

    kind: ControllerKind
    left_x: float
    left_y: float
    right_x: float
    right_y: float
    left_trigger: float
    right_trigger: float
    buttons: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        return {
            "device": self.kind.value,
            "lx": self.left_x,
            "ly": self.left_y,
            "rx": self.right_x,
            "ry": self.right_y,
            "lt": self.left_trigger,
            "rt": self.right_trigger,
            "buttons": list(self.buttons),
        }


_BUTTON_MAP: dict[ControllerKind, dict[str, str]] = {
    ControllerKind.XBOX: {
        "a": "south",
        "b": "east",
        "x": "west",
        "y": "north",
        "lb": "left_shoulder",
        "rb": "right_shoulder",
        "lt": "left_trigger",
        "rt": "right_trigger",
        "view": "select",
        "menu": "start",
        "l3": "left_stick",
        "r3": "right_stick",
        "dpad_up": "dpad_up",
        "dpad_down": "dpad_down",
        "dpad_left": "dpad_left",
        "dpad_right": "dpad_right",
    },
    ControllerKind.PS5: {
        "cross": "south",
        "circle": "east",
        "square": "west",
        "triangle": "north",
        "l1": "left_shoulder",
        "r1": "right_shoulder",
        "l2": "left_trigger",
        "r2": "right_trigger",
        "create": "select",
        "options": "start",
        "l3": "left_stick",
        "r3": "right_stick",
        "dpad_up": "dpad_up",
        "dpad_down": "dpad_down",
        "dpad_left": "dpad_left",
        "dpad_right": "dpad_right",
    },
    ControllerKind.SWITCH: {
        "b": "south",
        "a": "east",
        "y": "west",
        "x": "north",
        "l": "left_shoulder",
        "r": "right_shoulder",
        "zl": "left_trigger",
        "zr": "right_trigger",
        "minus": "select",
        "plus": "start",
        "l3": "left_stick",
        "r3": "right_stick",
        "dpad_up": "dpad_up",
        "dpad_down": "dpad_down",
        "dpad_left": "dpad_left",
        "dpad_right": "dpad_right",
    },
}


def _coerce_kind(kind: ControllerKind | str) -> ControllerKind:
    try:
        if isinstance(kind, ControllerKind):
            return kind
        return ControllerKind(kind.lower())
    except ValueError as exc:
        supported = ", ".join(k.value for k in ControllerKind)
        raise ValueError(
            f"unsupported controller kind {kind!r}; expected one of {supported}"
        ) from exc


def _normalise_axis(value: int, deadzone: float) -> float:
    raw = max(-32768, min(32767, value))
    scaled = raw / 32767 if raw >= 0 else raw / 32768

    magnitude = abs(scaled)
    if magnitude <= deadzone:
        return 0.0

    adjusted = (magnitude - deadzone) / (1.0 - deadzone)
    signed = adjusted if scaled > 0 else -adjusted
    return round(max(-1.0, min(1.0, signed)), 4)


def _normalise_trigger(value: int) -> float:
    return round(max(0, min(255, value)) / 255, 4)


def _normalise_buttons(kind: ControllerKind, buttons: Iterable[str]) -> tuple[str, ...]:
    mapping = _BUTTON_MAP[kind]
    canonical: set[str] = set()
    unknown: list[str] = []

    for button in buttons:
        key = button.lower().replace("-", "_").replace(" ", "_")
        mapped = mapping.get(key)
        if mapped is None:
            unknown.append(button)
        else:
            canonical.add(mapped)

    if unknown:
        raise ValueError(f"unknown {kind.value} button(s): {', '.join(sorted(unknown))}")

    return tuple(sorted(canonical))


def normalize_controller_state(
    state: RawControllerState,
    *,
    deadzone: float = 0.08,
    invert_y: bool = True,
) -> NormalizedControllerInput:
    """Convert platform-specific controller state into Ironwall's canonical form."""
    if not 0 <= deadzone < 1:
        raise ValueError("deadzone must be >= 0 and < 1")

    kind = _coerce_kind(state.kind)
    y_sign = -1 if invert_y else 1

    return NormalizedControllerInput(
        kind=kind,
        left_x=_normalise_axis(state.left_x, deadzone),
        left_y=y_sign * _normalise_axis(state.left_y, deadzone),
        right_x=_normalise_axis(state.right_x, deadzone),
        right_y=y_sign * _normalise_axis(state.right_y, deadzone),
        left_trigger=_normalise_trigger(state.left_trigger),
        right_trigger=_normalise_trigger(state.right_trigger),
        buttons=_normalise_buttons(kind, state.buttons),
    )


def serialize_controller_input(input_state: NormalizedControllerInput) -> bytes:
    """Return deterministic bytes suitable for InputPacket.payload and HMAC signing."""
    return json.dumps(
        input_state.to_payload(),
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
