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
