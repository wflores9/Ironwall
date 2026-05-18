# Changelog

## [0.1.0] — 2026-05-17

### Added
- Initial open-source release of the Ironwall monorepo
- `core/` — shared crypto primitives (HMAC-SHA3-256, SHA3-256), Hedera client factory, structured logging
- `layer1_thinclient/` — ThinClient WebSocket loop, GameServer simulation harness, InputPacket wire format, `extract_pov()` fog-of-war boundary
- `layer2_signing/` — ModuleSigner (ECDSA P-256, CT log), TEEVerifier (SGX/SEV SIM + HW)
- `layer3_attest/` — RemoteAttestationBroker with 60s JWT re-attest loop, hypervisor defeat via `_tcb_fresh()`
- `layer4_hedera/` — HederaMatchRecorder (HCS), PlayerIdentity (device-bound keypairs), WageringProtocol (escrow + auto-settlement)
- `zk_anticheat/` — HumanConstraints circom circuit (PLONK), ZKProver Python wrapper, reaction-time + mouse-acceleration constraints
- `merkle_audit/` — InputMerkleTree with HMAC leaf binding, O(log n) proof generation, `verify_proof()` audit function
- Unit test suite: crypto, merkle, signing, attestation, Hedera recorder, ZK prover
- CI-ready Makefile, docker-compose (SGX sim + Hedera mirror), pyproject.toml

### Migrated
- XRPL → Hedera (HCS) in v5.0 for aBFT consensus and wagering integrity

### Notes
- `SGX_MODE=SIM` for all dev/CI environments
- Switch to `SGX_MODE=HW` on 11th-gen+ Intel before production PRs

## [0.2.0] — 2026-05-18

### Added — XRPL hardening layer (`layer4_xrpl/`)

- **`DualAnchorRecorder`** — commits match records to Hedera HCS + XRPL simultaneously via `asyncio.gather`. Both must succeed; partial anchoring rejected.
- **`XRPLMatchRecorder`** — anchors match fingerprint (match_id | merkle_root | sha3_256(tee_receipt) | ts) to XRPL as AccountSet + Memo transaction.
- **`XRPLEscrow`** — native protocol-level escrow (EscrowCreate / EscrowFinish) with zero bytecode attack surface. Condition keyed on Hedera consensus timestamp — funds cannot release without a valid HCS record (cross-chain dependency, no bridge).
- **`XRPLPlayerIdentity`** — device-bound XRPL account creation + XLS-20 non-transferable (soulbound) reputation NFT minting. Compatible with Ward Protocol / XLS-66.
- **`hooks/zk_verifier.ts`** — XLS-30 Hook (TypeScript / WASM) that validates a ZK proof hash in Hook state before allowing EscrowFinish. Replaces Hedera EVM PLONK verifier stub (#212) with a protocol-level gate.
- Unit tests for all XRPL components (stub mode, xrpl-py not required): 13 new tests, 65 total passing.

### Security rationale
Dual-anchoring requires an attacker to corrupt two independent ledgers with different consensus mechanisms to erase or forge a match record. XRPL native escrow eliminates the Solidity bytecode attack surface present in the Hedera EVM wagering contract.
