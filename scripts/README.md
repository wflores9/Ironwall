# Ironwall Scripts

## Full workflow

```
Publisher (one time)          Player (every launch)
─────────────────────         ─────────────────────────────────────
sign_modules.py               run_broker.py  (Python broker, keep running)
    │                               │
    ├─ signing_key.pem              └─ POST /attest  ◀── ironwall-launcher.exe
    ├─ known_hashes.json                                      │
    └─ .signatures.json                               scans game DLLs
                                                      verifies hashes
                                                      boots game.exe
```

---

## 1. Install Rust + build launcher (Windows)

```powershell
# Run as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force
.\scripts\install_rust_windows.ps1
```

Installs Rust, builds `ironwall_launcher/target/release/ironwall-launcher.exe`.

---

## 2. Sign game modules (publisher side)

```bash
# Generate signing keypair (one time)
python scripts/sign_modules.py --generate-key --key-out signing_key.pem

# Sign all DLLs in game directory
python scripts/sign_modules.py \
    --game-dir "C:\cod25" \
    --key signing_key.pem \
    --dev-id "activision-cod25" \
    --out known_hashes.json
```

Outputs:
- `known_hashes.json` — passed to launcher via `--known-hashes`
- `known_hashes.signatures.json` — loaded by broker via `--signatures`

---

## 3. Start the attestation broker (Python)

```bash
# Simple start (SIM mode, no signatures)
python scripts/run_broker.py

# With known signatures
python scripts/run_broker.py --signatures known_hashes.signatures.json

# Production (SGX hardware)
python scripts/run_broker.py --sgx-mode HW --signatures known_hashes.signatures.json
```

Broker runs at `http://127.0.0.1:8766` by default.

---

## 4. Launch the game

```powershell
ironwall-launcher.exe `
  --game-dir  "C:\cod25" `
  --game-exe  "C:\cod25\cod.exe" `
  --player-id "your-player-id" `
  --known-hashes "known_hashes.json" `
  --broker-url "http://127.0.0.1:8766"
```

What happens:
1. Launcher scans all DLLs in `C:\cod25` with SHA3-256
2. Submits manifest to broker at `/attest`
3. Broker verifies hashes against signatures, runs TEE attestation
4. Broker issues 60-second JWT session token
5. Launcher boots `cod.exe` with token injected as `IRONWALL_SESSION_TOKEN` env var
6. Game's thin client uses token on first WebSocket connect

---

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SGX_MODE` | `SIM` | `SIM` = software emulation, `HW` = real SGX hardware |
| `SESSION_SECRET` | dev default | JWT signing secret — **change in production** |
| `ATTEST_HOST` | `127.0.0.1` | Broker bind host |
| `ATTEST_PORT` | `8766` | Broker bind port |
