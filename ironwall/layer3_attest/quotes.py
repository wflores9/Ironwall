"""Provider-aware quote verification for remote attestation receipts."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, padding, rsa


class AttestationProvider(StrEnum):
    """TEE attestation providers supported by the broker."""

    SIM = "sim"
    INTEL_SGX = "intel_sgx"
    AMD_SEV = "amd_sev"


@dataclass(frozen=True)
class QuoteVerificationResult:
    """Result returned by provider-specific quote verification."""

    ok: bool
    provider: AttestationProvider | None
    reason: str = ""


def verify_quote_signature(
    attest: dict[str, Any],
    *,
    sgx_mode: str = "SIM",
) -> QuoteVerificationResult:
    """Verify that an attestation receipt came from an accepted provider."""
    if "sgx_quote" in attest:
        return _verify_sgx_attestation(attest, sgx_mode=sgx_mode)
    if "amd_sev_report" in attest:
        return _verify_amd_attestation(attest, sgx_mode=sgx_mode)
    return QuoteVerificationResult(False, None, "missing attestation quote")


def _verify_sgx_attestation(
    attest: dict[str, Any],
    *,
    sgx_mode: str,
) -> QuoteVerificationResult:
    quote = attest.get("sgx_quote")
    if not isinstance(quote, str) or not quote:
        return QuoteVerificationResult(False, AttestationProvider.INTEL_SGX, "missing SGX quote")

    if quote.startswith("SIM_QUOTE_"):
        if sgx_mode == "HW":
            return QuoteVerificationResult(
                False,
                AttestationProvider.SIM,
                "SIM quote rejected in HW mode",
            )
        return QuoteVerificationResult(True, AttestationProvider.SIM)

    report = attest.get("ias_report")
    signature = attest.get("ias_signature")
    certificate = attest.get("ias_signing_cert")
    if not isinstance(report, dict):
        return QuoteVerificationResult(
            False,
            AttestationProvider.INTEL_SGX,
            "missing Intel IAS report",
        )

    status = report.get("isvEnclaveQuoteStatus")
    if status not in {"OK", "GROUP_OUT_OF_DATE"}:
        return QuoteVerificationResult(
            False,
            AttestationProvider.INTEL_SGX,
            f"bad IAS status {status!r}",
        )

    encoded_body = report.get("isvEnclaveQuoteBody")
    if not isinstance(encoded_body, str) or not _base64_decodes(encoded_body):
        return QuoteVerificationResult(
            False,
            AttestationProvider.INTEL_SGX,
            "invalid IAS quote body",
        )

    if not _verify_signed_report(report, signature, certificate):
        return QuoteVerificationResult(
            False,
            AttestationProvider.INTEL_SGX,
            "invalid IAS signature or signing certificate",
        )

    return QuoteVerificationResult(True, AttestationProvider.INTEL_SGX)


def _verify_amd_attestation(
    attest: dict[str, Any],
    *,
    sgx_mode: str,
) -> QuoteVerificationResult:
    report = attest.get("amd_sev_report")
    if not isinstance(report, str) or not report:
        return QuoteVerificationResult(False, AttestationProvider.AMD_SEV, "missing AMD SEV report")

    if report.startswith("SIM_QUOTE_"):
        if sgx_mode == "HW":
            return QuoteVerificationResult(
                False,
                AttestationProvider.SIM,
                "SIM report rejected in HW mode",
            )
        return QuoteVerificationResult(True, AttestationProvider.SIM)

    kds_report = attest.get("amd_kds_report")
    signature = attest.get("amd_kds_signature")
    certificate_chain = attest.get("amd_kds_cert_chain")
    if not isinstance(kds_report, dict):
        return QuoteVerificationResult(
            False,
            AttestationProvider.AMD_SEV,
            "missing AMD KDS report",
        )

    status = kds_report.get("status")
    if status not in {"OK", "CURRENT"}:
        return QuoteVerificationResult(
            False,
            AttestationProvider.AMD_SEV,
            f"bad AMD KDS status {status!r}",
        )

    encoded_report = kds_report.get("report")
    if not isinstance(encoded_report, str) or not _base64_decodes(encoded_report):
        return QuoteVerificationResult(
            False,
            AttestationProvider.AMD_SEV,
            "invalid AMD report body",
        )

    signing_material = (
        certificate_chain[0]
        if isinstance(certificate_chain, list) and certificate_chain
        else None
    )
    if not _verify_signed_report(kds_report, signature, signing_material):
        return QuoteVerificationResult(
            False,
            AttestationProvider.AMD_SEV,
            "invalid AMD KDS signature or certificate chain",
        )

    return QuoteVerificationResult(True, AttestationProvider.AMD_SEV)


def quote_from_fixture(payload: dict[str, Any]) -> str:
    """Build a deterministic REAL quote fixture body for tests and demos."""
    return "REAL_" + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def canonical_report_bytes(report: dict[str, Any]) -> bytes:
    """Return the signed report bytes used by local provider fixtures."""
    return json.dumps(report, separators=(",", ":"), sort_keys=True).encode()


def _base64_decodes(value: str) -> bool:
    try:
        base64.b64decode(value, validate=True)
    except Exception:
        return False
    return True


def _verify_signed_report(report: dict[str, Any], signature: Any, signing_material: Any) -> bool:
    if not isinstance(signature, str) or not isinstance(signing_material, str):
        return False

    try:
        signature_bytes = base64.b64decode(signature, validate=True)
        verifier = _load_verifier(signing_material.encode())
        signed_bytes = canonical_report_bytes(report)
        _verify_with_public_key(verifier, signature_bytes, signed_bytes)
    except Exception:
        return False

    return True


def _load_verifier(data: bytes) -> Any:
    try:
        return x509.load_pem_x509_certificate(data).public_key()
    except ValueError:
        return serialization.load_pem_public_key(data)


def _verify_with_public_key(public_key: Any, signature: bytes, data: bytes) -> None:
    if isinstance(public_key, rsa.RSAPublicKey):
        public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        return
    if isinstance(public_key, ec.EllipticCurvePublicKey):
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        return
    if isinstance(public_key, ed25519.Ed25519PublicKey):
        public_key.verify(signature, data)
        return
    raise InvalidSignature("unsupported public key type")
