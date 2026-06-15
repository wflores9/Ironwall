"""Unit tests for engine integration bridge payloads."""

import json
from pathlib import Path

import pytest

from ironwall.layer1_thinclient.engine_bridge import (
    EngineInputEvent,
    build_engine_input,
    serialize_engine_input,
)


def test_engine_input_serialization_is_deterministic() -> None:
    event = EngineInputEvent(
        engine="unity",
        player_id="player-1",
        sequence=7,
        timestamp_ns=123,
        actions={"fire": False, "move_y": 1.0, "move_x": 0.5},
    )

    first = serialize_engine_input(event)
    second = serialize_engine_input(event)

    assert first == second
    assert json.loads(first)["engine"] == "unity"
    assert b'"sequence":7' in first


def test_build_engine_input_rejects_unknown_engine() -> None:
    with pytest.raises(ValueError):
        build_engine_input(
            engine="godot",
            player_id="player-1",
            sequence=0,
            timestamp_ns=1,
            actions={},
        )


def test_samples_exist_for_unity_and_unreal() -> None:
    assert Path("samples/unity/IronwallUnityClient.cs").exists()
    assert Path("samples/unreal/IronwallUnrealClient.h").exists()
    assert Path("samples/unreal/IronwallUnrealClient.cpp").exists()


def test_unity_sample_reads_session_token() -> None:
    source = Path("samples/unity/IronwallUnityClient.cs").read_text(encoding="utf-8")

    assert "IRONWALL_SESSION_TOKEN" in source
    assert "Authorization" in source


def test_unreal_sample_reads_session_token() -> None:
    source = Path("samples/unreal/IronwallUnrealClient.cpp").read_text(encoding="utf-8")

    assert "IRONWALL_SESSION_TOKEN" in source
    assert "Authorization" in source
