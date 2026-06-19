/**
 * ironwall / layer4_xrpl / hooks / zk_verifier.ts
 * ─────────────────────────────────────────────────
 * XLS-30 Hook: validate a ZK proof hash before allowing escrow settlement.
 *
 * Why Hooks-based ZK verification hardens the system:
 *   The PLONK verifier is currently stubbed for Hedera EVM.
 *   An XLS-30 Hook runs at the ledger layer — before any funds move —
 *   with less attack surface than a Solidity contract (no EVM, no ABI
 *   encoding bugs, no reentrancy). The Hook rejects EscrowFinish
 *   transactions that don't carry a valid proof hash in their Memo field.
 *
 * Hook trigger: ttESCROW_FINISH (transaction type 3)
 *
 * Memo field spec (required on EscrowFinish):
 *   MemoType:   "69726f6e77616c6c5f7a6b5f70726f6f66"  ("ironwall_zk_proof")
 *   MemoData:   hex(sha3_256(plonk_proof_json))
 *   MemoFormat: "6170706c69636174696f6e2f6a736f6e"    ("application/json")
 *
 * Proof hash validation:
 *   The Hook checks the proof hash against the on-ledger registry
 *   (stored as Hook state: match_id → proof_hash). The server writes
 *   the proof hash to Hook state via a SetHookState transaction after
 *   the ZKProver.generate_proof() call succeeds.
 *
 * Build:
 *   npm install -g @xrplf/hooks-toolkit
 *   npx hsc compile zk_verifier.ts -o zk_verifier.wasm
 *
 * Deploy:
 *   See scripts/deploy_hook.ts
 *
 * Pending enhancements:
 *   - Complete PLONK verifier integration (Hedera EVM + XRPL Hook)
 *   - Benchmark Hook execution cost (fee units) on Hooks v3 testnet
 */

// ── Hook API types (from @xrplf/hooks-toolkit) ────────────────────────────
declare function hook_account(): ArrayBuffer;
declare function otxn_field(field_id: number): ArrayBuffer;
declare function otxn_type(): number;
declare function hook_state(key: ArrayBuffer): ArrayBuffer | null;
declare function hook_state_set(value: ArrayBuffer, key: ArrayBuffer): number;
declare function accept(msg: string, code: number): never;
declare function rollback(msg: string, code: number): never;
declare function util_sha256(data: ArrayBuffer): ArrayBuffer;
declare function slot_subfield(slot: number, field_id: number): number;
declare function otxn_slot(slot: number): number;
declare function slot_count(slot: number): number;
declare function slot_subarray(slot: number, index: number, dest: number): number;

// XRPL field IDs
const sfMemos        = 0xF00C;  // array of Memo objects
const sfMemo         = 0xEA01;
const sfMemoType     = 0x7C01;
const sfMemoData     = 0x7D01;

// Transaction types
const ttESCROW_FINISH = 3;

// Memo type we require: "ironwall_zk_proof" (hex)
const REQUIRED_MEMO_TYPE = "69726f6e77616c6c5f7a6b5f70726f6f66";

// Hook state key prefix for proof hashes: "proof_" + match_id
const PROOF_KEY_PREFIX = "70726f6f665f";  // "proof_"

// ── Utility ────────────────────────────────────────────────────────────────

function bufToHex(buf: ArrayBuffer): string {
    return Array.from(new Uint8Array(buf))
        .map(b => b.toString(16).padStart(2, "0"))
        .join("");
}

function hexToBuf(hex: string): ArrayBuffer {
    const arr = new Uint8Array(hex.length / 2);
    for (let i = 0; i < hex.length; i += 2) {
        arr[i / 2] = parseInt(hex.slice(i, i + 2), 16);
    }
    return arr.buffer;
}

function bufEqual(a: ArrayBuffer, b: ArrayBuffer): boolean {
    const ua = new Uint8Array(a);
    const ub = new Uint8Array(b);
    if (ua.length !== ub.length) return false;
    for (let i = 0; i < ua.length; i++) {
        if (ua[i] !== ub[i]) return false;
    }
    return true;
}

// ── Hook entrypoint ────────────────────────────────────────────────────────

export function hook(): number {
    // Only intercept EscrowFinish transactions
    if (otxn_type() !== ttESCROW_FINISH) {
        accept("Not EscrowFinish — pass through", 0);
    }

    // ── Step 1: Extract Memos array ────────────────────────────────────
    const memosSlot = otxn_slot(0);
    if (memosSlot < 0) {
        rollback("IW-ZK: No memos on EscrowFinish — proof required", 1);
    }

    const memoCount = slot_count(memosSlot);
    let proofHashHex: string | null = null;
    let matchIdHex: string | null = null;

    for (let i = 0; i < memoCount; i++) {
        const memoSlot = slot_subarray(memosSlot, i, 10 + i);
        const innerSlot = slot_subfield(memoSlot, sfMemo);

        const memoTypeSlot = slot_subfield(innerSlot, sfMemoType);
        const memoDataSlot = slot_subfield(innerSlot, sfMemoData);

        if (memoTypeSlot < 0 || memoDataSlot < 0) continue;

        const memoType = otxn_field(sfMemoType);
        const memoTypeHex = bufToHex(memoType).toLowerCase();

        if (memoTypeHex === REQUIRED_MEMO_TYPE) {
            const memoData = otxn_field(sfMemoData);
            proofHashHex = bufToHex(memoData).toLowerCase();
        }

        // Also extract match_id from a separate memo if present
        // (MemoType: "69726f6e77616c6c5f6d617463685f6964" = "ironwall_match_id")
        if (memoTypeHex === "69726f6e77616c6c5f6d617463685f6964") {
            const memoData = otxn_field(sfMemoData);
            matchIdHex = bufToHex(memoData).toLowerCase();
        }
    }

    if (!proofHashHex) {
        rollback("IW-ZK: Missing ironwall_zk_proof memo — EscrowFinish rejected", 2);
    }

    // ── Step 2: Load expected proof hash from Hook state ──────────────
    // Key: sha256("proof_" + match_id_hex)
    if (!matchIdHex) {
        rollback("IW-ZK: Missing ironwall_match_id memo — cannot verify proof", 3);
    }

    const stateKeyRaw = PROOF_KEY_PREFIX + matchIdHex;
    const stateKey = hexToBuf(stateKeyRaw);
    const stateKeyHash = util_sha256(stateKey);

    const expectedProofHashBuf = hook_state(stateKeyHash);
    if (!expectedProofHashBuf) {
        rollback("IW-ZK: No proof hash registered for this match — settlement rejected", 4);
    }

    const expectedProofHashHex = bufToHex(expectedProofHashBuf!).toLowerCase();

    // ── Step 3: Compare submitted hash vs registered hash ─────────────
    if (proofHashHex !== expectedProofHashHex) {
        rollback(
            `IW-ZK: Proof hash mismatch — submitted=${proofHashHex!.slice(0, 8)}… ` +
            `expected=${expectedProofHashHex.slice(0, 8)}…`,
            5
        );
    }

    // ── Step 4: Accept — proof verified, funds can move ───────────────
    accept("IW-ZK: ZK proof hash verified — EscrowFinish approved", 0);
}

/**
 * Separate entrypoint called when the server registers a proof hash
 * in Hook state before settlement.
 *
 * Called via: SetHookState transaction from the Ironwall server wallet.
 * Key:   sha256("proof_" + match_id_hex)
 * Value: sha3_256(plonk_proof_json) — 32 bytes
 */
export function hook_set_proof(matchIdHex: string, proofHash: ArrayBuffer): void {
    const stateKeyRaw = PROOF_KEY_PREFIX + matchIdHex;
    const stateKey = hexToBuf(stateKeyRaw);
    const stateKeyHash = util_sha256(stateKey);
    const result = hook_state_set(proofHash, stateKeyHash);
    if (result < 0) {
        rollback("IW-ZK: Failed to register proof hash in Hook state", 6);
    }
}
