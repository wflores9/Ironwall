# Ironwall C++ SDK

Header-only C++ interface for integrating Ironwall into AAA engines — Unreal Engine, CoD-engine, and any custom C++ game engine.

## Architecture

The C++ SDK is a thin client. It handles:
- Binary hash verification against `known_hashes.json` at launch
- Session attestation requests to the Ironwall broker
- Match record submission for dual-chain anchoring

Heavy lifting (TEE attestation, Merkle tree construction, XRPL/Hedera anchoring) runs in the **Ironwall broker** — a FastAPI service (`ironwall-cloud`) that the SDK communicates with over HTTPS. The broker runs server-side; the SDK never needs SGX or Hedera SDK dependencies in the game binary.

## Integration

Copy `ironwall.h` into your project. No build system changes required — header-only.

```cpp
#include "ironwall.h"
```

Link against `libcurl` (or your engine's HTTP client) for the underlying broker calls.

## Usage

### 1. At game launch — attest binary + establish session

```cpp
ironwall::IronwallClient client(
    "https://broker.ironwall.example.com",
    "YOUR_STUDIO_API_KEY"
);

ironwall::SessionToken token;
ironwall::Result result = client.attest(player_id, token);

if (!result.success) {
    // Binary tampered or TEE attestation failed — hard deny
    TerminateSession(result.error);
    return;
}
// token.token is valid for 60 seconds
```

### 2. Every 60 seconds during match — re-validate session

```cpp
// Call on a background thread, 60s interval
if (!client.validate(token)) {
    // Session invalidated — attestation expired or enclave tampered
    TerminateMatch("SESSION_INVALID");
}
```

### 3. At match end — submit record for on-chain anchoring

```cpp
ironwall::MatchRecord record;
record.match_id    = GenerateMatchId();
record.merkle_root = GetInputMerkleRoot();   // from server-side Merkle tree
record.receipt_hash = GetReceiptHash();      // from TEE attestation receipt
record.end_time    = UnixTimestampMs();

ironwall::Result anchor = client.commit_match(record, token);
if (anchor.success) {
    // anchor.data contains JSON: {"xrpl_tx": "...", "hedera_ts": "..."}
}
```

### 4. Independent verification — no trust in Ironwall servers

```cpp
// Anyone can call this with just the match ID
ironwall::Result verify = ironwall::IronwallClient::verify(match_id, "mainnet");
if (verify.success) {
    // verify.data contains the on-chain record — enforcement decision is provable
}
```

## Broker

The SDK communicates with the Ironwall broker (`ironwall-cloud`), a FastAPI service that wraps:
- `ironwall.layer3_attest.broker.RemoteAttestationBroker` — TEE attestation + JWT session tokens
- `ironwall.layer4_xrpl.recorder.DualAnchorRecorder` — dual-chain anchoring (XRPL + Hedera HCS)

See the [Python broker source](../../layer3_attest/broker.py) and [XRPL recorder](../../layer4_xrpl/recorder.py) for the server-side implementation.
