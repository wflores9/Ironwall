# Changelog

## [Unreleased] — hardening

### Security
- **Ed25519 asymmetric JWT signing** (`layer3_attest/broker.py`): replaced symmetric HS256 `SESSION_SECRET` with ephemeral or supplied Ed25519 keypair. Tokens are signed with the private key and verified with the public key — symmetric-key forgery is no longer possible.
- **Production quote verification** (`layer3_attest/quotes.py`): SGX/SEV quote verification now distinguishes SIM, Intel IAS/DCAP, and AMD KDS receipts. `SGX_MODE=HW` rejects SIM fixtures and requires provider report, signature, and certificate-chain material.
- **Pinned MRENCLAVE verification** (`layer3_attest/broker.py`): `_verify_mrenclave()` now checks the quote measurement against `IRONWALL_EXPECTED_MRENCLAVE` or `IRONWALL_MRENCLAVE_FILE`; `SGX_MODE=HW` requires a configured pin.
- **Publisher public key auto-registration** (`layer3_attest/broker.py`): on broker init, `signing_key.pub.pem` is loaded and registered with `TEEVerifier` under `PUBLISHER_DEV_ID` (default `ironwall-cod`), eliminating a manual bootstrap step.
- **CT log → Hedera HCS** (`layer2_signing/signer.py`, `core/hedera.py`): `_anchor_ct_log()` no longer writes to `ct_log.jsonl`. It now calls `write_ct_log_hedera()` which submits the entry to a Hedera HCS topic (`HEDERA_CT_LOG_TOPIC_ID`) as a `TopicMessageSubmitTransaction`. The SDK call is stubbed but the interface is fully wired; set the env var to activate in production.
- **`.gitignore` hardening**: added `*.pem`, `*.jsonl`, `target/` to prevent accidental commits of private keys, CT logs, and Rust build artefacts.

### Fixed
- **`scripts/sign_modules.py` duplicate-filename dedup** (`build_known_hashes`): changed return type from `dict[str, str]` to `dict[str, list[str]]`. When the same DLL filename appears in multiple subdirectories with different content, all hashes are stored. The scanner now accepts any matching hash.
- **`ironwall_launcher/src/scanner.rs` path-aware dedup**: `ScanConfig.known_hashes` changed from `HashMap<String, String>` to `HashMap<String, Vec<String>>`. `has_signature` is true when the scanned SHA3-256 matches *any* entry in the list — same-filename DLLs in different subdirectories with different hashes are each registered and accepted separately.
- **ZK circuit build path** (`Makefile`): `make circuits` now creates `zk/` and compiles the circuit from `ironwall/zk_anticheat/circuits/human_constraints.circom`.
- **Game-server compose target** (`Dockerfile.gameserver`): added the missing image definition used by `docker-compose.yml`.

### Added
- **GitHub Actions CI** (`.github/workflows/ci.yml`): runs `cargo test` in `ironwall_launcher/` and `pytest tests/unit/` (with `SESSION_SECRET` and `SGX_MODE=SIM`) on every push and PR to `main`.
- **`scanner.rs` test** `multi_hash_any_match_accepted`: verifies that a DLL whose hash matches the second entry in a multi-hash list is correctly marked `has_signature = true`.
- **Public match-record verifier** (`ironwall.cli.verify`): adds the `ironwall-verify record.json` CLI for validating full Hedera records, Hedera stub receipts, and XRPL fingerprints before dispute review or public audit.
- **Verification demo fixtures** (`examples/`, `make verify-demo`): adds a valid match record and a tampered record so the audit path can be demonstrated locally in one command.
- **Controller input normalisation** (`layer1_thinclient/controller.py`): canonicalises Xbox, PS5, and Switch axes, triggers, and buttons into deterministic payload bytes for HMAC signing and Merkle audit.
- **Unity / Unreal integration samples** (`samples/`): adds engine sample clients plus canonical engine input bridge payload helpers for launcher-injected session tokens.
- **PLONK verifier commitments** (`zk_anticheat/commitment.py`, `layer4_hedera/contracts/PlonkVerifierRegistry.sol`): adds a shared proof commitment format plus a Hedera EVM registry/adapter for snarkjs-generated PLONK verifiers and XRPL Hook proof-hash gates.

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
- **`hooks/zk_verifier.ts`** — XLS-30 Hook (TypeScript / WASM) that validates a ZK proof hash in Hook state before allowing EscrowFinish. Replaces the Hedera EVM PLONK verifier stub with a protocol-level gate.
- Unit tests for all XRPL components (stub mode, xrpl-py not required): 13 new tests, 65 total passing.

### Security rationale
Dual-anchoring requires an attacker to corrupt two independent ledgers with different consensus mechanisms to erase or forge a match record. XRPL native escrow eliminates the Solidity bytecode attack surface present in the Hedera EVM wagering contract.
