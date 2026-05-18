pragma circom 2.1.6;

/*
 * Project Ironwall — ZK Anti-Cheat Module
 * Circuit: HumanConstraints
 * ─────────────────────────────────────────
 * Encodes physical human performance constraints as arithmetic constraints.
 * A player generates a SNARK proof with each input batch proving their
 * actions were physically achievable. The server verifies cryptographically —
 * no ML heuristics, no statistical false positives.
 *
 * We use PLONK (not Groth16) — no trusted setup required, appropriate for
 * a public-facing anti-cheat system. Groth16 maintained for legacy only.
 *
 * Current constraints:
 *   1. Reaction time   ≥ 80ms between aimed shots
 *   2. Mouse accel     ≤ 4000 cm/s² (empirical human max)
 *
 * Contributing: new constraints require peer review by a biomechanics or
 * human-factors researcher + empirical data citations in the PR.
 *
 * Open bounties:
 *   #201 — Scroll-wheel input rate constraint         [500 HBAR]
 *   #204 — Controller trigger timing constraint       [500 HBAR]
 */

include "../../../node_modules/circomlib/circuits/comparators.circom";

template HumanConstraints(n_inputs) {
    // ── Private signals (hidden from verifier) ────────────────────────
    // Raw timing deltas between consecutive input events (ms)
    signal input deltas[n_inputs];
    // Mouse acceleration magnitude per input event (cm/s²)
    signal input mouse_accel[n_inputs];

    // ── Public output ─────────────────────────────────────────────────
    signal output valid;

    // ── Constraint instantiation ──────────────────────────────────────
    component min_rt[n_inputs];
    component max_acc[n_inputs];

    for (var i = 0; i < n_inputs; i++) {

        // ── Constraint 1: Reaction time ≥ 80ms ───────────────────────
        // Minimum human reaction time between aimed shots.
        // Below 80ms is considered physically impossible for aimed fire.
        // Source: Fitts' Law + empirical FPS reaction time studies.
        min_rt[i] = GreaterEqThan(32);
        min_rt[i].in[0] <== deltas[i];
        min_rt[i].in[1] <== 80;   // 80ms floor
        min_rt[i].out === 1;

        // ── Constraint 2: Mouse acceleration ≤ 4000 cm/s² ────────────
        // Maximum observed human mouse acceleration.
        // Above 4000 cm/s² indicates synthetic/scripted input.
        // Source: empirical gaming peripheral studies.
        max_acc[i] = LessEqThan(32);
        max_acc[i].in[0] <== mouse_accel[i];
        max_acc[i].in[1] <== 4000;  // 4000 cm/s² empirical max
        max_acc[i].out === 1;

        // TODO #201: scroll-wheel input rate constraint
        // TODO #204: controller trigger timing constraint
    }

    valid <== 1;
}

// Public input: n_inputs (batch size, fixed at 32 for proof efficiency)
component main {public [n_inputs]} = HumanConstraints(32);
