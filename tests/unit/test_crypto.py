"""Unit tests for core crypto primitives."""

import hashlib
import pytest

from ironwall.core.crypto import sha3_256_hex, hmac_sign, hmac_verify


KEY = b"a" * 32
KEY2 = b"b" * 32


class TestSha3:
    def test_matches_stdlib(self):
        data = b"hello ironwall"
        assert sha3_256_hex(data) == hashlib.sha3_256(data).hexdigest()

    def test_str_input(self):
        assert sha3_256_hex("hello") == hashlib.sha3_256(b"hello").hexdigest()

    def test_not_sha256(self):
        data = b"test"
        assert sha3_256_hex(data) != hashlib.sha256(data).hexdigest()


class TestHmac:
    def test_sign_verify_roundtrip(self):
        payload = b"player input bytes"
        tag = hmac_sign(payload, KEY)
        assert hmac_verify(payload, tag, KEY)

    def test_wrong_key_fails(self):
        tag = hmac_sign(b"data", KEY)
        assert not hmac_verify(b"data", tag, KEY2)

    def test_tampered_payload_fails(self):
        tag = hmac_sign(b"data", KEY)
        assert not hmac_verify(b"tampered", tag, KEY)

    def test_tag_is_32_bytes(self):
        tag = hmac_sign(b"x", KEY)
        assert len(tag) == 32
