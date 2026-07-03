# Ironwall FAQ

## What does Ironwall actually do?

Ironwall runs across the full game lifecycle — not just at ban time.

**Pre-game:** the Rust launcher scans every game module DLL/binary, verifies SHA3-256 hashes against `known_hashes.json`, checks ECDSA signatures against the developer's public key, and confirms the scan ran inside a tamper-proof TEE enclave. Any mismatch = hard deny before the player ever connects.

**In-game:** TEE attestation re-verifies the session every 60 seconds. A compromised session is terminated immediately.

**Post-game:** every enforcement decision produces a cryptographic receipt — Merkle-committed inputs, TEE attestation quote, dual-anchored to XRPL and Hedera HCS. Anyone can run `ironwall-verify <match-id>` from their own machine to confirm the ban was legitimate without trusting Ironwall's servers.

---

## How is this different from kernel-level anti-cheat?

Kernel anti-cheat (Vanguard, EAC, BattlEye) wins on runtime detection depth — ring-0 access sees everything during a match. Ironwall doesn't replace that.

Ironwall wins on provability. Every ban produces a cryptographic receipt anyone can independently verify. Vanguard can't prove a ban was legitimate. Ironwall can.

Used together: Ironwall catches file tampering before launch, kernel anti-cheat handles runtime detection, Ironwall anchors the enforcement decision on-chain permanently.

---

## What is anyone actually verifying with ironwall-verify?

Three things:

1. **The exact binary that ran** — SHA3-256 hash signed by the developer at build time
2. **The inputs were committed** — every player input Merkle-hashed, root anchored on-chain
3. **The enforcement decision** — ban record permanently anchored to XRPL + Hedera, tamper-proof

Nobody — including Ironwall — can alter that record after the fact.

---

## Does Ironwall require kernel access?

No. The launcher operates at user-space + TEE level. No ring-0 driver, no permanent background process, no compatibility issues with Linux or security software.
