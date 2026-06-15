"""Command-line verification for Ironwall match records."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ironwall.core.crypto import sha3_256_hex


Hex64 = str


@dataclass(frozen=True)
class VerificationResult:
    """Structured result for a match-record verification run."""

    ok: bool
    record_type: str
    match_id: str | None = None
    merkle_root: str | None = None
    receipt_hash: str | None = None
    errors: list[str] = field(default_factory=list)


def _is_hex64(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value.lower())
    )


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("record JSON must contain an object")
    return data


def _normalise_record(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Accept raw records plus Hedera stub and XRPL fingerprint wrappers."""
    if isinstance(payload.get("record"), dict):
        return "hedera_record", payload["record"]

    fingerprint = payload.get("fingerprint")
    if isinstance(fingerprint, dict):
        if isinstance(fingerprint.get("data"), dict):
            return "xrpl_fingerprint", fingerprint["data"]
        if isinstance(fingerprint.get("hex"), str):
            decoded = json.loads(fingerprint["hex"])
            if isinstance(decoded, dict):
                return "xrpl_fingerprint", decoded

    return "match_record", payload


def _receipt_hash(receipt: dict[str, Any]) -> Hex64:
    return sha3_256_hex(json.dumps(receipt, sort_keys=True))


def _receipt_is_attested(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    if receipt.get("verified") is True:
        return True
    if receipt.get("status") == "ATTESTED":
        return True
    return isinstance(receipt.get("sgx_quote"), str) or isinstance(
        receipt.get("amd_sev_report"), str
    )


def verify_match_record(payload: dict[str, Any]) -> VerificationResult:
    """Verify the local structure and cryptographic fields of a match record."""
    record_type, record = _normalise_record(payload)
    errors: list[str] = []

    match_id = record.get("match_id")
    merkle_root = record.get("merkle_root")
    receipt_hash = record.get("receipt_hash")

    if not isinstance(match_id, str) or not match_id:
        errors.append("missing match_id")

    if not _is_hex64(merkle_root):
        errors.append("merkle_root must be a 64-character SHA3-256 hex digest")

    if "ts" not in record:
        errors.append("missing ts")

    if record_type == "xrpl_fingerprint":
        if not _is_hex64(receipt_hash):
            errors.append("receipt_hash must be a 64-character SHA3-256 hex digest")
    else:
        players = record.get("players")
        outcome_hash = record.get("outcome_hash")
        tee_receipt = record.get("tee_receipt")

        if not isinstance(players, list) or not players:
            errors.append("players must be a non-empty list")
        if not _is_hex64(outcome_hash):
            errors.append("outcome_hash must be a 64-character SHA3-256 hex digest")
        if not _receipt_is_attested(tee_receipt):
            errors.append("tee_receipt must contain an attested TEE receipt")
        elif isinstance(tee_receipt, dict):
            receipt_hash = _receipt_hash(tee_receipt)

    return VerificationResult(
        ok=not errors,
        record_type=record_type,
        match_id=match_id if isinstance(match_id, str) else None,
        merkle_root=merkle_root if isinstance(merkle_root, str) else None,
        receipt_hash=receipt_hash if isinstance(receipt_hash, str) else None,
        errors=errors,
    )


def _result_to_dict(result: VerificationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "record_type": result.record_type,
        "match_id": result.match_id,
        "merkle_root": result.merkle_root,
        "receipt_hash": result.receipt_hash,
        "errors": result.errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ironwall-verify",
        description="Verify an Ironwall match record or XRPL fingerprint JSON file.",
    )
    parser.add_argument("record", type=Path, help="Path to a match record JSON file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        payload = _load_json(args.record)
        result = verify_match_record(payload)
    except Exception as exc:
        result = VerificationResult(False, "unknown", errors=[str(exc)])

    if args.json:
        print(json.dumps(_result_to_dict(result), sort_keys=True))
    elif result.ok:
        print(f"OK match={result.match_id} merkle={result.merkle_root}")
    else:
        print("FAIL " + "; ".join(result.errors), file=sys.stderr)

    return 0 if result.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
