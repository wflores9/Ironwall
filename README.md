# PROJECT IRONWALL

**Open-source anti-cheat protocol stack.**
Thin client · TEE attestation · ZK-SNARKs · Hedera HCS

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Hedera Mainnet](https://img.shields.io/badge/hedera-mainnet-4a90d9)](https://hedera.com)

---

## Architecture

```
[PLAYER DEVICE]  →  [LAYER 2: Module Signing / TEE]  →  [LAYER 3: Remote Attestation]
      ↓                                                           ↓
[LAYER 1: Game Server]  →  [LAYER 4: Hedera HCS]  →  [VERIFIED MATCH RECORD]
```

Four layers form a sequential trust chain. A compromised or missing component
at any layer results in **hard session denial** — never degraded security.

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| 1 | ThinClient / GameServer | Input capture, server-side simulation, H.264 stream |
| 2 | ModuleSigner / TEEVerifier | ECDSA P-256 build-time signing, SGX/SEV runtime verification |
| 3 | RemoteAttestationBroker | 60-second re-attest loop, session token gating |
| 4 | HederaMatchRecorder | Immutable HCS match record, reputation, wagering |
| ZK | ZKProver / HumanConstraints | PLONK proof of physical human input constraints |
| Audit | InputMerkleTree | Per-input HMAC leaves, auditable Merkle root on HCS |

---

## Quick Start

### Prerequisites

- Python 3.11+ (3.12 recommended)
- Rust 1.75+ (optional — Layer 1 perf-critical paths)
- Node.js 20+ (ZK circuit tooling)
- Docker 24+ (integration test harness, SGX emulation)

### Install

```bash
git clone https://github.com/wflores9/Ironwall.git
cd ironwall

# Python deps
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Node deps (ZK tooling)
npm install

# Compile ZK circuits (~2 min first run)
make circuits
```

### Configure

```bash
cp .env.example .env
# fill in HEDERA_OPERATOR_ID, HEDERA_OPERATOR_KEY, IRONWALL_TOPIC_ID
```

> **SGX_MODE=SIM** uses Intel's software simulation — no SGX hardware required for development.
> Switch to `SGX_MODE=HW` on a compatible machine (11th-gen+ Intel) before production PRs.

### Run Tests

```bash
make test-unit          # fast, no external deps
make test-integration   # requires docker-compose up -d
make test-zk            # ZK circuit tests (~5 min)
make cov                # coverage report
```

---

## Repository Structure

```
ironwall/
├── core/                   # Shared crypto, logging, Hedera client
├── layer1_thinclient/      # Thin client + game server simulation
├── layer2_signing/         # ECDSA module signing + TEE verifier
├── layer3_attest/          # Remote attestation broker + session mgmt
├── layer4_hedera/          # HCS match recorder, identity, wagering
├── zk_anticheat/           # ZK-SNARK circuit + proof generation
│   └── circuits/           # circom circuit definitions
├── merkle_audit/           # Input Merkle tree + audit trail
├── tests/
│   ├── unit/               # Fast, no external deps
│   └── integration/        # Docker-based full-stack tests
└── docs/                   # Architecture diagrams
```

---

## Security Model

- **Trust boundary**: everything client-side is adversarial. The game server and on-chain layer are the only trusted components.
- **extract_pov()** is the fog-of-war boundary. It must never include entity positions outside the player's visibility cone.
- **SHA3-256 only** in all crypto paths — never SHA-256 (length-extension attack risk).
- **Pinned MRENCLAVE**: set `IRONWALL_EXPECTED_MRENCLAVE` or `IRONWALL_MRENCLAVE_FILE` from a reproducible-build artifact before running `SGX_MODE=HW`.
- **Quote verification logic**: `SGX_MODE=HW` rejects SIM quotes and validates Intel IAS/DCAP or AMD KDS report structure, signature, and certificate-chain material against the supplied report. This logic is implemented and unit-tested; it has not yet been run against live Intel IAS / AMD KDS endpoints or real SGX/SEV hardware — see Roadmap.
- **Hypervisor defeat**: Intel SGX TCB measurement flags virtualisation. Ring-1 cheats fail `_tcb_fresh()` + `_no_debug_flag()` → hard session denial.
- **Hard deny, never degrade**: missing attestation, stale token, or CT log mismatch all terminate the session. There is no "reduced trust" mode.

## Roadmap

**Landed:**
- [x] Public match-record verification CLI (`ironwall-verify --match-id <tx>`)
- [x] Controller input normalisation (Xbox / PS5 / Switch)
- [x] Unreal / Unity sample integration (`samples/`)
- [x] MRENCLAVE pinning mechanism + reproducible-build hook
- [x] SGX/SEV quote verification logic — signature and certificate-chain checks for Intel IAS and AMD KDS report formats, SIM/HW mode gating (unit-tested, not yet run against live attestation services)
- [x] PLONK verifier registry contract (Hedera EVM) + XRPL Hook scaffold for proof-hash gating on escrow settlement

**Pending — requires hardware/business steps, not just code:**
- [ ] Live Intel IAS / AMD KDS integration — requires Intel/AMD developer enrollment and API credentials
- [ ] Run quote verification against real SGX/SEV-enabled hardware
- [ ] PLONK proof verification circuit — the registry contract currently accepts an external `IPlonkVerifier`; the verifier implementation itself (trusted setup + circuit) is not yet built
- [ ] End-to-end demo: launch → attest → capture → anchor → verify, recorded on real (non-SIM) hardware where possible

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full PR checklist and code style guide.

### Good First Issues

| Issue | Description |
|-------|-------------|
| #112 | Adaptive bitrate for video encoder (Layer 1) |
| #118 | Controller input normalisation: Xbox / PS5 / Switch |
| #145 | CLI tool: verify a match record from HCS topic |
| #151 | Python type stubs for hedera-sdk-py integration |
| #163 | Improve test coverage for InputMerkleTree edge cases |

### Bounty Program

| Issue | Description | Bounty |
|-------|-------------|--------|
| #89 | Rust rewrite of capture_input() — sub-1ms latency | 500 HBAR |
| #97 | Security audit: extract_pov() speculative visibility leak | 1000 HBAR |
| #198 | ZK proof gen benchmark on low-end hardware | 250 HBAR |
| #201 | Scroll-wheel input rate constraint (circom) | 500 HBAR |
| #204 | Controller trigger timing constraint (circom) | 500 HBAR |
| #212 | PLONK verifier contract — Hedera EVM | 750 HBAR |

### Security Disclosure

Do **not** open a public GitHub issue for security vulnerabilities.  
Report via [GitHub private vulnerability reporting](https://github.com/wflores9/Ironwall/security/advisories/new) — 24-hour acknowledgement, 14-day patch target.  
Critical vulnerabilities (extract_pov, TEEVerifier, attestation bypass) eligible for out-of-band bounties up to **5000 HBAR**.

## FAQ

See [docs/faq.md](docs/faq.md) for the full FAQ.

**What does Ironwall actually do?**

Ironwall runs across the full game lifecycle — not just at ban time.

Pre-game: the Rust launcher scans every game module DLL/binary, verifies SHA3-256 hashes against `known_hashes.json`, checks ECDSA signatures against the developer's public key, and confirms the scan ran inside a tamper-proof TEE enclave. Any mismatch = hard deny before the player ever connects.

In-game: TEE attestation re-verifies the session every 60 seconds. A compromised session is terminated immediately.

Post-game: every enforcement decision produces a cryptographic receipt — Merkle-committed inputs, TEE attestation quote, dual-anchored to XRPL and Hedera HCS. Anyone can run `ironwall-verify <match-id>` from their own machine to confirm the ban was legitimate without trusting Ironwall's servers.

**How is this different from kernel-level anti-cheat?**

Kernel anti-cheat (Vanguard, EAC, BattlEye) wins on runtime detection depth — ring-0 access sees everything during a match. Ironwall doesn't replace that.

Ironwall wins on provability. Every ban produces a cryptographic receipt anyone can independently verify. Vanguard can't prove a ban was legitimate. Ironwall can.

Used together: Ironwall catches file tampering before launch, kernel anti-cheat handles runtime detection, Ironwall anchors the enforcement decision on-chain permanently.

**Does Ironwall require kernel access?**

No. The launcher operates at user-space + TEE level. No ring-0 driver, no permanent background process, no compatibility issues with Linux or security software.

---

## License

MIT — see [LICENSE](LICENSE).

*Build the infrastructure that ends the arms race.*  
[github.com/wflores9/Ironwall](https://github.com/wflores9/Ironwall)
