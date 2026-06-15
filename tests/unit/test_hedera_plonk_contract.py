"""Static checks for the Hedera PLONK verifier registry contract."""

from pathlib import Path


CONTRACT = Path("ironwall/layer4_hedera/contracts/PlonkVerifierRegistry.sol")


def test_contract_exposes_verifier_adapter() -> None:
    source = CONTRACT.read_text(encoding="utf-8")

    assert "interface IPlonkVerifier" in source
    assert "function verifyAndRegister" in source
    assert "function registerCommitment" in source


def test_contract_uses_canonical_offchain_hashes() -> None:
    source = CONTRACT.read_text(encoding="utf-8")

    assert "bytes32 proofHash" in source
    assert "bytes32 publicSignalsHash" in source
    assert "keccak256" not in source
