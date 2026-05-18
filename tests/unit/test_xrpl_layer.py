"""
Unit tests for layer4_xrpl — stub mode (xrpl-py not required).

Tests cover:
  - XRPLMatchRecorder fingerprint construction + stub commit
  - DualAnchorRecorder parallel dispatch
  - XRPLEscrow condition/preimage math + verify_preimage()
  - XRPLEscrow create/finish stub paths
"""

from __future__ import annotations

import hashlib
import pytest

# ── XRPLMatchRecorder ─────────────────────────────────────────────────────

from ironwall.layer4_xrpl.recorder import XRPLMatchRecorder, DualAnchorRecorder

VALID_RESULT = {
    "id": "match-xrpl-0001",
    "player_ids": ["rAlice000", "rBob0000"],
    "outcome_hash": "a" * 64,
    "input_merkle_root": "b" * 64,
    "end_time": 1_700_000_000_000,
}
VALID_ATTEST = {"verified": True, "receipt": {"sgx_quote": "SIM_QUOTE_abc"}}
UNATTESTED   = {"verified": False}


@pytest.fixture
def xrpl_recorder():
    return XRPLMatchRecorder(wallet=None, network="testnet")


class TestXRPLMatchRecorder:
    @pytest.mark.asyncio
    async def test_unattested_raises(self, xrpl_recorder):
        with pytest.raises(ValueError, match="Unattested"):
            await xrpl_recorder.commit_match_record(VALID_RESULT, UNATTESTED)

    @pytest.mark.asyncio
    async def test_stub_returns_tx_hash(self, xrpl_recorder):
        receipt = await xrpl_recorder.commit_match_record(VALID_RESULT, VALID_ATTEST)
        assert "tx_hash" in receipt
        assert "fingerprint" in receipt

    def test_fingerprint_contains_merkle_root(self, xrpl_recorder):
        fp = xrpl_recorder._build_fingerprint(VALID_RESULT, VALID_ATTEST)
        assert fp["data"]["merkle_root"] == VALID_RESULT["input_merkle_root"]

    def test_fingerprint_receipt_hash_is_sha3(self, xrpl_recorder):
        import json
        fp = xrpl_recorder._build_fingerprint(VALID_RESULT, VALID_ATTEST)
        expected = hashlib.sha3_256(
            json.dumps(VALID_ATTEST, sort_keys=True).encode()
        ).hexdigest()
        assert fp["data"]["receipt_hash"] == expected

    def test_different_attestations_different_fingerprints(self, xrpl_recorder):
        attest2 = {"verified": True, "receipt": {"sgx_quote": "DIFFERENT"}}
        fp1 = xrpl_recorder._build_fingerprint(VALID_RESULT, VALID_ATTEST)
        fp2 = xrpl_recorder._build_fingerprint(VALID_RESULT, attest2)
        assert fp1["data"]["receipt_hash"] != fp2["data"]["receipt_hash"]


# ── DualAnchorRecorder ────────────────────────────────────────────────────

class TestDualAnchorRecorder:
    @pytest.mark.asyncio
    async def test_both_receipts_returned(self):
        """Both Hedera and XRPL receipts should be in the result."""
        from unittest.mock import AsyncMock

        hedera_mock = AsyncMock()
        hedera_mock.commit_match_record.return_value = {
            "consensus_timestamp": "1700000000.000000000"
        }
        xrpl_mock = AsyncMock()
        xrpl_mock.commit_match_record.return_value = {
            "tx_hash": "ABCDEF1234"
        }

        recorder = DualAnchorRecorder(hedera_mock, xrpl_mock)
        anchors = await recorder.commit(VALID_RESULT, VALID_ATTEST)

        assert "hedera" in anchors
        assert "xrpl" in anchors
        assert anchors["hedera"]["consensus_timestamp"] == "1700000000.000000000"
        assert anchors["xrpl"]["tx_hash"] == "ABCDEF1234"

    @pytest.mark.asyncio
    async def test_hedera_failure_propagates(self):
        from unittest.mock import AsyncMock
        hedera_mock = AsyncMock()
        hedera_mock.commit_match_record.side_effect = RuntimeError("HCS down")
        xrpl_mock = AsyncMock()
        xrpl_mock.commit_match_record.return_value = {"tx_hash": "OK"}

        recorder = DualAnchorRecorder(hedera_mock, xrpl_mock)
        with pytest.raises(RuntimeError, match="HCS down"):
            await recorder.commit(VALID_RESULT, VALID_ATTEST)


# ── XRPLEscrow ────────────────────────────────────────────────────────────

from ironwall.layer4_xrpl.escrow import XRPLEscrow


@pytest.fixture
def escrow():
    return XRPLEscrow(wallet=None, network="testnet")


class TestXRPLEscrow:
    def test_condition_preimage_roundtrip(self, escrow):
        """sha256(preimage) == condition — the core crypto invariant."""
        condition, preimage = escrow._build_condition(
            "match-001",
            placeholder=False,
            hedera_consensus_ts="1700000000.000000000",
            merkle_root="c" * 64,
        )
        assert XRPLEscrow.verify_preimage(condition, preimage)

    def test_placeholder_condition_differs_from_real(self, escrow):
        """Placeholder (creation) condition != settled condition."""
        cond_placeholder, _ = escrow._build_condition("match-001", placeholder=True)
        cond_real, _ = escrow._build_condition(
            "match-001",
            placeholder=False,
            hedera_consensus_ts="1700000000.000000000",
            merkle_root="c" * 64,
        )
        assert cond_placeholder != cond_real

    def test_different_matches_different_conditions(self, escrow):
        c1, _ = escrow._build_condition("match-001", placeholder=True)
        c2, _ = escrow._build_condition("match-002", placeholder=True)
        assert c1 != c2

    def test_verify_preimage_wrong_preimage_fails(self, escrow):
        condition, _ = escrow._build_condition("match-001", placeholder=True)
        bad_preimage = "00" * 32
        assert not XRPLEscrow.verify_preimage(condition, bad_preimage)

    @pytest.mark.asyncio
    async def test_create_wager_stub(self, escrow):
        result = await escrow.create_wager(
            player_a="rAlice000",
            player_b="rBob0000",
            amount_xrp=10.0,
            match_id="match-escrow-001",
        )
        assert "escrow_sequence" in result
        assert "condition" in result
        assert result["match_id"] == "match-escrow-001"

    @pytest.mark.asyncio
    async def test_finish_wager_stub(self, escrow):
        result = await escrow.finish_wager(
            escrow_owner="rServer000",
            escrow_sequence=12345,
            match_id="match-escrow-001",
            hedera_consensus_ts="1700000000.000000000",
            merkle_root="d" * 64,
            winner_address="rAlice000",
        )
        assert result["winner"] == "rAlice000"
