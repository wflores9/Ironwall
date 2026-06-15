"""Unit tests for controller input normalisation."""

import pytest

from ironwall.layer1_thinclient.controller import (
    ControllerKind,
    RawControllerState,
    normalize_controller_state,
    serialize_controller_input,
)


def test_xbox_axes_triggers_and_buttons_normalize() -> None:
    normalized = normalize_controller_state(
        RawControllerState(
            kind="xbox",
            left_x=32767,
            left_y=-32768,
            right_x=0,
            right_y=4096,
            left_trigger=128,
            right_trigger=255,
            buttons=["A", "RB", "Menu", "dpad-left"],
        )
    )

    assert normalized.kind == ControllerKind.XBOX
    assert normalized.left_x == 1.0
    assert normalized.left_y == 1.0
    assert normalized.right_x == 0.0
    assert normalized.right_y < 0
    assert normalized.left_trigger == 0.502
    assert normalized.right_trigger == 1.0
    assert normalized.buttons == ("dpad_left", "right_shoulder", "south", "start")


def test_ps5_buttons_map_to_same_canonical_layout() -> None:
    normalized = normalize_controller_state(
        RawControllerState(kind=ControllerKind.PS5, buttons=["Cross", "R1", "Options"])
    )

    assert normalized.buttons == ("right_shoulder", "south", "start")


def test_switch_buttons_map_to_same_canonical_layout() -> None:
    normalized = normalize_controller_state(
        RawControllerState(kind="switch", buttons=["B", "R", "Plus"])
    )

    assert normalized.buttons == ("right_shoulder", "south", "start")


def test_deadzone_suppresses_small_axis_drift() -> None:
    normalized = normalize_controller_state(
        RawControllerState(kind="xbox", left_x=1200, left_y=-1200),
        deadzone=0.08,
    )

    assert normalized.left_x == 0.0
    assert normalized.left_y == 0.0


def test_unknown_controller_kind_fails() -> None:
    with pytest.raises(ValueError, match="unsupported controller kind"):
        normalize_controller_state(RawControllerState(kind="stadia"))


def test_unknown_button_fails_closed() -> None:
    with pytest.raises(ValueError, match="unknown xbox button"):
        normalize_controller_state(RawControllerState(kind="xbox", buttons=["paddle_1"]))


def test_serialized_payload_is_deterministic() -> None:
    normalized = normalize_controller_state(
        RawControllerState(kind="ps5", left_x=32767, buttons=["Options", "Cross"])
    )

    payload_1 = serialize_controller_input(normalized)
    payload_2 = serialize_controller_input(normalized)

    assert payload_1 == payload_2
    assert b'"buttons":["south","start"]' in payload_1
    assert b'"lx":1.0' in payload_1
