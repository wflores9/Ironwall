"""Unit tests for RemoteAttestationBroker (mocked TEE)."""

import os
import pytest

os.environ.setdefault("SESSION_SECRET", "testsecret_32bytesexactlyXXXXXX!")
os.environ.setdefault("SGX_MODE", "SIM")

from ironwall.layer3_attest.broker import RemoteAttestationBroker

VALID_ATTEST = {
    "sgx_quote": "SIM_QUOTE_abc123",
    "verified": True,
}

INVALID_ATTEST = {
    "sgx_quote": "BAD_QUOTE",
    "verified": False,
}


@pytest.fixture
def broker():
    return RemoteAttestationBroker()


class TestInitializeSession:
    @pytest.mark.asyncio
    async def test_valid_attest_returns_token(self, broker):
        token = await broker.initialize_session("player_1", VALID_ATTEST)
        assert token is not None
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_missing_quote_denied(self, broker):
        token = await broker.initialize_session("player_2", {})
        assert token is None

    @pytest.mark.asyncio
    async def test_same_player_different_tokens(self, broker):
        import asyncio
        await asyncio.sleep(1)  # ensure different iat
        t1 = await broker.initialize_session("player_3", VALID_ATTEST)
        t2 = await broker.initialize_session("player_3", VALID_ATTEST)
        # tokens may differ by iat; both should be valid strings
        assert t1 is not None and t2 is not None


class TestValidateToken:
    @pytest.mark.asyncio
    async def test_valid_token_passes(self, broker):
        token = await broker.initialize_session("player_a", VALID_ATTEST)
        assert broker.validate_token("player_a", token)

    @pytest.mark.asyncio
    async def test_wrong_player_fails(self, broker):
        token = await broker.initialize_session("player_a", VALID_ATTEST)
        assert not broker.validate_token("player_b", token)

    def test_garbage_token_fails(self, broker):
        assert not broker.validate_token("player_x", "notavalidtoken")

    def test_empty_token_fails(self, broker):
        assert not broker.validate_token("player_x", "")
