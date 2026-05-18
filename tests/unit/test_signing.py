"""Unit tests for ModuleSigner and TEEVerifier (SGX_MODE=SIM)."""

import os
import pathlib
import pytest

os.environ.setdefault("SGX_MODE", "SIM")

from ironwall.layer2_signing.signer import ModuleSigner
from ironwall.layer2_signing.tee_verifier import TEEVerifier, register_public_key


@pytest.fixture
def keypair():
    priv_pem, pub_pem = ModuleSigner.generate_key_pem()
    return priv_pem, pub_pem


@pytest.fixture
def signer(keypair):
    priv_pem, _ = keypair
    return ModuleSigner(priv_pem)


class TestModuleSigner:
    def test_sign_returns_required_fields(self, signer):
        code = b"fake module binary"
        record = signer.sign_module(code, "test_dev")
        assert {"dev_id", "mod_hash", "sig", "ts", "ct_anchor"} <= record.keys()

    def test_mod_hash_is_sha3_256(self, signer):
        import hashlib
        code = b"module"
        record = signer.sign_module(code, "test_dev")
        expected = hashlib.sha3_256(code).hexdigest()
        assert record["mod_hash"] == expected

    def test_different_code_different_hash(self, signer):
        r1 = signer.sign_module(b"code_a", "dev")
        r2 = signer.sign_module(b"code_b", "dev")
        assert r1["mod_hash"] != r2["mod_hash"]

    def test_wrong_curve_raises(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = rsa_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        with pytest.raises((ValueError, Exception)):
            ModuleSigner(pem)


class TestTEEVerifier:
    def test_valid_module_attested(self, keypair, tmp_path, monkeypatch):
        import ironwall.layer2_signing.signer as smod
        import ironwall.layer2_signing.tee_verifier as tmod

        priv_pem, pub_pem = keypair
        register_public_key("test_dev2", pub_pem)

        ct_log = tmp_path / "ct_log.jsonl"
        monkeypatch.setattr(smod, "_CT_LOG_PATH", ct_log)

        orig_path = tmod.Path
        monkeypatch.setattr(
            tmod, "Path",
            lambda p: ct_log if "ct_log" in str(p) else orig_path(p)
        )

        s = ModuleSigner(priv_pem)
        code = b"legit game module"
        record = s.sign_module(code, "test_dev2")
        v = TEEVerifier()
        result = v.verify_and_attest(code, record)
        assert result["status"] == "ATTESTED"
        assert result["verified"] is True

    def test_tampered_binary_banned(self, keypair, tmp_path, monkeypatch):
        import ironwall.layer2_signing.signer as smod
        priv_pem, pub_pem = keypair
        register_public_key("dev_tamper", pub_pem)
        monkeypatch.setattr(smod, "_CT_LOG_PATH", tmp_path / "ct_log.jsonl")
        s = ModuleSigner(priv_pem)
        code = b"legit module"
        record = s.sign_module(code, "dev_tamper")
        v = TEEVerifier()
        result = v.verify_and_attest(b"tampered module", record)
        assert result["status"] == "BANNED"
        assert result["reason"] == "HASH_MISMATCH"

    def test_unknown_dev_id_banned(self, keypair, tmp_path, monkeypatch):
        import ironwall.layer2_signing.signer as smod
        priv_pem, _ = keypair
        monkeypatch.setattr(smod, "_CT_LOG_PATH", tmp_path / "ct_log2.jsonl")
        s = ModuleSigner(priv_pem)
        code = b"module"
        record = s.sign_module(code, "unknown_dev_999")
        v = TEEVerifier()
        result = v.verify_and_attest(code, record)
        assert result["status"] == "BANNED"
        assert result["reason"] in ("UNKNOWN_DEV_ID", "CT_LOG_MISMATCH")
