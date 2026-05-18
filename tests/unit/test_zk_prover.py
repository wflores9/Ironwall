"""
Unit tests for ZKProver.

These tests do NOT invoke snarkjs (slow, requires compiled circuits).
They test input validation, padding helpers, and the subprocess interface
via mocking. For full circuit tests run: make test-zk
"""

import json
import pytest
from unittest.mock import MagicMock, patch

from ironwall.zk_anticheat.prover import ZKProver, _BATCH_SIZE


@pytest.fixture
def prover(tmp_path):
    zkey = tmp_path / "test.zkey"
    vkey = tmp_path / "vkey.json"
    zkey.touch()
    vkey.write_text(json.dumps({"protocol": "plonk"}))
    return ZKProver(zkey_path=zkey, vkey_path=vkey)


class TestPadBatch:
    def test_pads_to_batch_size(self):
        result = ZKProver.pad_batch([100, 200, 150], fill=100)
        assert len(result) == _BATCH_SIZE
        assert result[:3] == [100, 200, 150]
        assert all(v == 100 for v in result[3:])

    def test_already_full(self):
        values = [90] * _BATCH_SIZE
        assert ZKProver.pad_batch(values) == values

    def test_too_large_raises(self):
        with pytest.raises(ValueError):
            ZKProver.pad_batch([1] * (_BATCH_SIZE + 1))


class TestGenerateProof:
    def test_wrong_length_raises(self, prover):
        with pytest.raises(ValueError):
            prover.generate_proof([100] * 10, [200] * 10)

    def test_calls_snarkjs(self, prover):
        deltas = ZKProver.pad_batch([100] * 10)
        accel = ZKProver.pad_batch([500] * 10)

        fake_proof = {"pi_a": ["1", "2"], "pi_b": [["3", "4"]], "pi_c": ["5", "6"]}

        with patch("ironwall.zk_anticheat.prover.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Write fake proof.json in the tmpdir used by generate_proof
            import ironwall.zk_anticheat.prover as pmod
            original_tmp = pmod.tempfile.TemporaryDirectory

            class FakeTmp:
                def __init__(self): self.name = "/tmp/fake_zk_test"
                def __enter__(self):
                    import os, pathlib
                    os.makedirs(self.name, exist_ok=True)
                    pathlib.Path(self.name + "/proof.json").write_text(json.dumps(fake_proof))
                    pathlib.Path(self.name + "/public.json").write_text("[]")
                    return self.name
                def __exit__(self, *a): pass

            with patch.object(pmod.tempfile, "TemporaryDirectory", FakeTmp):
                proof = prover.generate_proof(deltas, accel)

            assert "pi_a" in proof


class TestVerify:
    def test_ok_in_stdout_returns_true(self, prover):
        fake_proof = {"pi_a": []}
        with patch("ironwall.zk_anticheat.prover.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"[INFO]  OK!", returncode=0)
            import ironwall.zk_anticheat.prover as pmod

            class FakeTmp:
                def __init__(self): self.name = "/tmp/fake_verify"
                def __enter__(self):
                    import os
                    os.makedirs(self.name, exist_ok=True)
                    return self.name
                def __exit__(self, *a): pass

            with patch.object(pmod.tempfile, "TemporaryDirectory", FakeTmp):
                result = prover.verify(fake_proof, [1])
            assert result is True

    def test_missing_ok_returns_false(self, prover):
        with patch("ironwall.zk_anticheat.prover.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=b"[ERROR] Invalid proof", returncode=1)
            import ironwall.zk_anticheat.prover as pmod

            class FakeTmp:
                def __init__(self): self.name = "/tmp/fake_verify2"
                def __enter__(self):
                    import os
                    os.makedirs(self.name, exist_ok=True)
                    return self.name
                def __exit__(self, *a): pass

            with patch.object(pmod.tempfile, "TemporaryDirectory", FakeTmp):
                result = prover.verify({}, [0])
            assert result is False
