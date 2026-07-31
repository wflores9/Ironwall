# Ironwall — Streamer / Studio Demo

## 30-second pitch
Ironwall is an open anti-cheat layer: TEE attestation, ZK movement proofs (Groth16 + Halo2), and dual anchors on Hedera HCS + XRPL.

## Run the demo
    git clone https://github.com/wflores9/Ironwall.git
    cd Ironwall
    ./scripts/demo_thin_stack.sh

## What you will see
1. Clean movement — proof accepted + combined hash
2. Speedhack — rejected + ban strike
3. Matchmaker pairs players
4. Optional sim chain anchors (Hashscan / XRPL testnet links)

## Branding
- Logos: assets/ironwall-*.png
- Banner: printed by thin client + verifier at startup

## For COD / Unreal teams
See cpp-thin-client/unreal/ plugin stub and C ABI (include/ironwall/c_api.h).
