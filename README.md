# Ironwall

Open-source anti-cheat protocol stack.

## Thin Client (Rust)

- TEE attestation placeholder (SGX / SEV / Nitro / TrustZone ready)
- ZK-SNARK movement validation stub (physics-plausible movement proofs)
- Dual anchoring: Hedera HCS + XRPL

### Quick start

    cargo run

### Architecture

    src/
    ├── main.rs          # entrypoint
    ├── thin_client.rs   # client loop
    ├── tee.rs           # TEE quote generation
    ├── zk.rs            # ZK movement proofs
    ├── anchors.rs       # HCS + XRPL dual anchor
    └── config.rs        # runtime config

### Roadmap

- [x] Thin client skeleton
- [x] TEE attestation placeholder
- [x] ZK movement proof stub
- [x] HCS + XRPL dual anchor
- [ ] Real TEE integration (DCAP / SEV-SNP)
- [ ] arkworks / Halo2 movement circuit
- [ ] Live HCS topic submission
- [ ] XRPL memo / NFToken anchor
- [ ] Challenge-response dispute protocol
- [ ] Game engine SDKs (Unreal / Unity / custom)

### License

MIT OR Apache-2.0
