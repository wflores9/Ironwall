#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "=== Ironwall full thin-stack demo ==="
echo "root: $ROOT"

echo ""
echo "--- C++ build ---"
cd "$ROOT/cpp-thin-client"
cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build build -j"$(nproc)" >/dev/null
cd build
echo "[cpp] tests"
ctest --output-on-failure
echo "[cpp] thin_client"
./ironwall_thin_client | tail -8
echo "[cpp] verifier"
./ironwall_verifier | tail -8
echo "[cpp] matchmaker"
./ironwall_matchmaker | tail -10
echo "[cpp] chain_smoke"
./ironwall_chain_smoke | tail -6

echo ""
echo "--- Rust ---"
cd "$ROOT/rust-thin-client"
cargo test --release -q
echo "[rust] thin_client"
cargo run --release -q --bin ironwall_thin_client 2>&1 | tail -8
echo "[rust] verifier"
cargo run --release -q --bin ironwall_verifier 2>&1 | tail -8
echo "[rust] matchmaker"
cargo run --release -q --bin ironwall_matchmaker 2>&1 | tail -10

echo ""
echo "=== demo complete ==="
