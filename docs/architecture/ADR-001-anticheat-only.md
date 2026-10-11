# ADR-001: Ironwall Is Anti-Cheat Only

Status: PROPOSED — awaiting founder review and merge
Date: 2026-10-11
Scope: Ironwall only. No changes to Ward Protocol.

## Product mission
Ironwall is an anti-cheat product for video games: prevent and detect game tampering, validate competitive multiplayer actions, protect gaming sessions, and preserve tamper-evident anti-cheat evidence for game studios, multiplayer operators, and esports events.

Ironwall is **not** a generalized institutional workflow, credit, settlement, compliance, or financial-resolution product. It must not resemble, import, fork, depend on, or share service ownership with Ward Protocol. Ward is unaffected.

## Locked technical direction (proposed)
- **Rust**: launcher, game integrity verification, server-side anti-cheat services, secure session/attestation orchestration, cryptographic evidence, and blockchain-record verification.
- **C++20/23**: native game-engine SDK, Unreal and other performance-critical or platform-native hooks. Unity receives a maintained C ABI/.NET adapter.
- **TypeScript**: optional game-studio operator console and developer portal, no sensitive detection secrets.
- **XRPL and/or Hedera**: optional post-event anchoring of anti-cheat evidence commitments. Never on the latency-critical gameplay path; never a source of cheat detection or ban authority.
- **PostgreSQL/secure storage**: off-chain event data, operational state, reviewed evidence, retention, appeal records.
- Python can remain only for development scripts/tests until native replacements pass parity/security tests.

## What belongs in Ironwall
1. Signed game build/module integrity and launcher verification.
2. Server-authoritative checks and game-specific anti-cheat signals.
3. Supported platform attestation with genuine quote verification and replay protection.
4. Low-overhead telemetry, detection correlation, thresholds, false-positive analysis.
5. Secure evidence capture, audit hashes, independent verification and appeals.
6. Studio-controlled enforcement decisions, reversible sanctions, audit logs.
7. Engine SDKs and multiplayer server integrations.
8. Optional chain anchoring with truthful transaction status and explicit network IDs.

## Out of scope — reject or quarantine
- Ward policy engine, nine checks, institutional evidence-to-resolution flows, unsigned financial settlement packets.
- XRPL or Hedera wagering, escrow, prize payout, financial settlement and gambling features.
- Financial smart contracts or settlement-driven proof gates.
- Mandatory ledger writes for sessions or per-tick events.
- Claims that SHA/hashes alone are zero-knowledge proofs, simulated SGX quotes are hardware attestation, or blockchain inclusion proves gameplay was clean.
- Any claim of automatic hardware bans or ring-1/hypervisor cheat defeat without measurement and independent validation.

## Security and production gates
- SIM vs HW mode segregated in API, types, configuration, and evidence. SIM must never yield HW-certified evidence.
- Fail closed for required security checks, while blockchain anchoring failures must not silently create forged success receipts. Ledger outages are handled outside gameplay.
- Authenticated versioned transport; signed and expiring session tokens; replay-safe challenges; managed secrets and key rotation.
- Server-side authoritative corroboration before high-severity enforcement, appeal workflow, metrics for false positives and performance overhead.
- Measurable game-engine integration; Linux/macOS/Windows build and test parity; dependency scan, fuzzing, static analysis, adversarial tests, signed releases.
- Hardware-backed attestation only after validated on supported production devices.
- Prove cryptographic claims with real verifier/tests; otherwise describe as heuristic or hash commitments.
- No code/architectural changes to Ward Protocol.

## Initial audit evidence (source inspection, not complete test validation)
- Python `ironwall/layer1_thinclient/server.py`: placeholder world, renderer and POV.
- Python `ironwall/layer2_signing/tee_verifier.py`: local CT-log stub and simulated quote generation.
- Rust `rust-thin-client/src/tee.rs`: synthetic quote IDs, zero-filled enclave measurements.
- C++ `cpp-thin-client/src/tee.cpp`: synthetic measurements.
- Rust `rust-thin-client/src/zk.rs` and C++ `cpp-thin-client/src/zk.cpp`: hash-labelled movement proofs, not full ZK proofs.
- Python `ironwall/layer4_xrpl/recorder.py`: stub transaction fallback.
- Python `ironwall/layer4_xrpl/escrow.py` and `ironwall/layer4_hedera/wagering.py`: out-of-scope financial functionality.
- `ironwall_launcher/src/broker.rs`: Python attestation broker dependency.
- Actions 30673758148: Windows C++ configure failed while other five native jobs passed; investigate, do not claim all-platform green.

## Migration rules
1. Preserve baseline and record tests before removing code.
2. Replace Python services in small Rust slices with behavior/evidence conformance tests.
3. Consolidate competing Rust/C++ thin client security logic; avoid two independent implementations of critical attest/verification logic.
4. Quarantine wagering/escrow modules in a reviewable PR before removal, keeping history intact.
5. Add schema/protocol versioning, C ABI integration tests, packaging, and performance benchmarks.
6. Merge only after explicit founder approval and security gates.

## Acceptance definition
A reproducible game launch -> measured integrity check -> authenticated session -> server-validated cheat signal -> recorded evidence -> studio-reviewed enforcement -> independently verifiable evidence demonstration, with honest simulation boundaries and optional testnet ledger anchoring.
