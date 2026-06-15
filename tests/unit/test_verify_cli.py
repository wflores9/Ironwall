"""Unit tests for the ironwall-verify CLI."""

from __future__ import annotations

import json
from pathlib import Path

from ironwall.cli.verify import main, verify_match_record

REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_RECORD = {
    "match_id": "match-uuid-0001",
    "players": ["0.0.100", "0.0.101"],
    "outcome_hash": "a" * 64,
    "merkle_root": "b" * 64,
    "tee_receipt": {"sgx_quote": "SIM_QUOTE_abc", "status": "ATTESTED"},
    "ts": 1_700_000_000_000,
}


def test_full_match_record_verifies() -> None:
    result = verify_match_record(VALID_RECORD)
    assert result.ok
    assert result.record_type == "match_record"
    assert result.match_id == "match-uuid-0001"
    assert result.receipt_hash is not None


def test_hedera_stub_wrapper_verifies() -> None:
    result = verify_match_record({"consensus_timestamp": "STUB", "record": VALID_RECORD})
    assert result.ok
    assert result.record_type == "hedera_record"


def test_xrpl_fingerprint_verifies() -> None:
    result = verify_match_record(
        {
            "tx_hash": "STUB_XRPL_TX",
            "fingerprint": {
                "data": {
                    "match_id": "match-xrpl-0001",
                    "merkle_root": "c" * 64,
                    "receipt_hash": "d" * 64,
                    "ts": 1_700_000_000_000,
                }
            },
        }
    )
    assert result.ok
    assert result.record_type == "xrpl_fingerprint"


def test_invalid_merkle_root_fails() -> None:
    record = {**VALID_RECORD, "merkle_root": "not-a-root"}
    result = verify_match_record(record)
    assert not result.ok
    assert "merkle_root" in result.errors[0]


def test_unattested_record_fails() -> None:
    record = {**VALID_RECORD, "tee_receipt": {"status": "BANNED"}}
    result = verify_match_record(record)
    assert not result.ok
    assert "tee_receipt" in result.errors[-1]


def test_cli_json_success(tmp_path, capsys) -> None:
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(VALID_RECORD), encoding="utf-8")

    code = main([str(record_path), "--json"])
    out = json.loads(capsys.readouterr().out)

    assert code == 0
    assert out["ok"] is True
    assert out["match_id"] == "match-uuid-0001"


def test_cli_failure(tmp_path, capsys) -> None:
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps({"match_id": "bad"}), encoding="utf-8")

    code = main([str(record_path)])
    captured = capsys.readouterr()

    assert code == 1
    assert "FAIL" in captured.err


def test_example_valid_record_passes(capsys) -> None:
    code = main([str(REPO_ROOT / "examples" / "match-record-valid.json")])
    captured = capsys.readouterr()

    assert code == 0
    assert "OK match=demo-match-0001" in captured.out


def test_example_tampered_record_fails(capsys) -> None:
    code = main([str(REPO_ROOT / "examples" / "match-record-tampered.json")])
    captured = capsys.readouterr()

    assert code == 1
    assert "merkle_root" in captured.err
