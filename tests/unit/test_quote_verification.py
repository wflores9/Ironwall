"""Unit tests for provider-aware quote verification."""

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from ironwall.layer3_attest.quotes import (
    AttestationProvider,
    canonical_report_bytes,
    verify_quote_signature,
)


QUOTE_BODY = base64.b64encode(b"quote-body").decode()


def signing_fixture() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return public_key_pem, _sign_report(private_key, {"probe": "fixture"})


def _sign_report(private_key: rsa.RSAPrivateKey, report: dict[str, object]) -> str:
    signature = private_key.sign(
        canonical_report_bytes(report),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def intel_attest(status: str = "OK") -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    report = {
        "id": "ias-report-1",
        "isvEnclaveQuoteStatus": status,
        "isvEnclaveQuoteBody": QUOTE_BODY,
    }
    return {
        "sgx_quote": "REAL_" + "a" * 64,
        "ias_report": report,
        "ias_signature": _sign_report(private_key, report),
        "ias_signing_cert": public_key_pem,
    }


def amd_attest(status: str = "OK") -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    report = {
        "status": status,
        "report": QUOTE_BODY,
    }
    return {
        "amd_sev_report": "REAL_" + "b" * 64,
        "amd_kds_report": report,
        "amd_kds_signature": _sign_report(private_key, report),
        "amd_kds_cert_chain": [public_key_pem],
    }


def test_sim_quote_allowed_in_sim_mode() -> None:
    result = verify_quote_signature({"sgx_quote": "SIM_QUOTE_" + "a" * 64}, sgx_mode="SIM")

    assert result.ok
    assert result.provider == AttestationProvider.SIM


def test_sim_quote_rejected_in_hw_mode() -> None:
    result = verify_quote_signature({"sgx_quote": "SIM_QUOTE_" + "a" * 64}, sgx_mode="HW")

    assert not result.ok
    assert result.reason == "SIM quote rejected in HW mode"


def test_intel_ias_report_passes() -> None:
    result = verify_quote_signature(intel_attest(), sgx_mode="HW")

    assert result.ok
    assert result.provider == AttestationProvider.INTEL_SGX


def test_intel_ias_bad_status_fails() -> None:
    result = verify_quote_signature(intel_attest(status="CONFIGURATION_NEEDED"), sgx_mode="HW")

    assert not result.ok
    assert "bad IAS status" in result.reason


def test_intel_ias_missing_signature_fails() -> None:
    attest = intel_attest()
    attest["ias_signature"] = ""

    result = verify_quote_signature(attest, sgx_mode="HW")

    assert not result.ok
    assert "invalid IAS signature" in result.reason


def test_amd_kds_report_passes() -> None:
    result = verify_quote_signature(amd_attest(), sgx_mode="HW")

    assert result.ok
    assert result.provider == AttestationProvider.AMD_SEV


def test_amd_kds_bad_status_fails() -> None:
    result = verify_quote_signature(amd_attest(status="REVOKED"), sgx_mode="HW")

    assert not result.ok
    assert "bad AMD KDS status" in result.reason


def test_amd_kds_missing_cert_chain_fails() -> None:
    attest = amd_attest()
    attest["amd_kds_cert_chain"] = []

    result = verify_quote_signature(attest, sgx_mode="HW")

    assert not result.ok
    assert "invalid AMD KDS signature" in result.reason
