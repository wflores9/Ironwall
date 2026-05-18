"""Unit tests for HederaMatchRecorder (testnet fixtures / stub mode)."""

import pytest

from ironwall.layer4_hedera.recorder import HederaMatchRecorder

VALID_RESULT = {
    "id": "match-uuid-0001",
    "player_ids": ["0.0.100", "0.0.101"],
    "outcome_hash": "a" * 64,
    "input_merkle_root": "b" * 64,
    "end_time": 1_700_000_000_000,
}

VALID_ATTEST = {
    "verified": True,
    "receipt": {"sgx_quote": "SIM_QUOTE_abc", "status": "ATTESTED"},
}

UNATTESTED = {"verified": False}


@pytest.fixture
def recorder():
    # Stub client — hedera-sdk-py not required for unit tests
    return HederaMatchRecorder(client=None, topic_id="0.0.9999")


class TestCommitMatchRecord:
    @pytest.mark.asyncio
    async def test_unattested_raises(self, recorder):
        with pytest.raises(ValueError, match="Unattested"):
            await recorder.commit_match_record(VALID_RESULT, UNATTESTED)

    @pytest.mark.asyncio
    async def test_attested_returns_receipt(self, recorder):
        receipt = await recorder.commit_match_record(VALID_RESULT, VALID_ATTEST)
        assert receipt is not None

    @pytest.mark.asyncio
    async def test_record_contains_merkle_root(self, recorder):
        # Patch _SDK_AVAILABLE so we hit the stub path
        import ironwall.layer4_hedera.recorder as mod
        original = mod._SDK_AVAILABLE
        mod._SDK_AVAILABLE = False
        try:
            receipt = await recorder.commit_match_record(VALID_RESULT, VALID_ATTEST)
            assert receipt["record"]["merkle_root"] == VALID_RESULT["input_merkle_root"]
        finally:
            mod._SDK_AVAILABLE = original
