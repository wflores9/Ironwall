# Ironwall C++ Thin Client

AAA-ready C++20 anti-cheat thin client.

## Build

    mkdir build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    cmake --build . -j

## Run

    ./ironwall_thin_client
    ./ironwall_verifier
    ctest

## Features

- TEE attestation stub
- ZK movement validation + speedhack reject
- Hedera HCS + XRPL dual anchor
- Challenge-response
- Wire protocol (std::variant messages)
- Session + proof store
- In-process net loopback

## Binaries

| Binary | Description |
|--------|-------------|
| ironwall_thin_client | Player thin client |
| ironwall_verifier | Server verifier + moderation + lobby demo |
| ironwall_matchmaker | Matchmaking service |
| ironwall_chain_smoke | HCS/XRPL dual-anchor smoke |
| ironwall_replay | Replay match TSV logs |

## Full stack demo

From repo root:

    ./scripts/demo_thin_stack.sh
