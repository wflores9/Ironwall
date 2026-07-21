# Ironwall

Open-source anti-cheat protocol stack.

## Components

| Binary | Description |
|--------|-------------|
| ironwall_thin_client | Player-side thin client (TEE + ZK + dual anchor + net) |
| ironwall_verifier    | Verifier / server-side stub |

## Features (current)

- TEE attestation placeholder (SGX / SEV / Nitro / TrustZone ready)
- ZK-SNARK movement validation stub + speedhack rejection
- Hedera HCS + XRPL dual anchoring
- Challenge-response dispute protocol
- Wire protocol (ClientMessage / ServerMessage)
- Session tracking
- In-memory proof store
- Loopback net transport (mpsc) for local client-server demo
- Library + two binaries

## Quick start

    cargo run --bin ironwall_thin_client
    cargo run --bin ironwall_verifier
    cargo test

## Architecture

    src/
    ├── lib.rs           # public API (ironwall)
    ├── main.rs          # thin client binary
    ├── bin/verifier.rs  # verifier binary
    ├── tee.rs           # TEE quote generation
    ├── zk.rs            # ZK movement proofs + speed checks
    ├── anchors.rs       # HCS + XRPL dual anchor
    ├── challenge.rs     # challenge-response
    ├── protocol.rs      # wire messages
    ├── session.rs       # session state
    ├── net.rs           # loopback transport
    ├── store.rs         # proof store
    ├── config.rs
    ├── error.rs
    └── thin_client.rs   # movement simulation loop

## Roadmap

- [x] Thin client skeleton
- [x] TEE attestation placeholder
- [x] ZK movement proof stub + speedhack detect
- [x] HCS + XRPL dual anchor
- [x] Challenge-response
- [x] Wire protocol
- [x] Session + proof store
- [x] Loopback net + verifier binary
- [ ] Real TEE (DCAP / SEV-SNP)
- [ ] arkworks / Halo2 circuit
- [ ] Live HCS + XRPL submission
- [ ] QUIC / WebSocket transport
- [ ] Persistent store (sled / sqlite)
- [ ] Game engine SDKs

## License

MIT OR Apache-2.0
