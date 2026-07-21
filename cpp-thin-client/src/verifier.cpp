#include "ironwall/ironwall.hpp"
#include <iostream>

int main() {
    using namespace ironwall;
    std::cout << "Ironwall C++ Verifier starting...\n";

    Config cfg;
    TeeAttestation tee;
    auto att = tee.generate();
    std::cout << "Verifier TEE quote: " << att.quote_hash << "\n";

    ZkMovementValidator zk(cfg.max_speed);

    try {
        auto ok = zk.prove("player_001", {0,0,0}, {0.1f,0,0}, 50);
        std::cout << "Clean proof accepted: true\n";

        HcsAnchor hcs(cfg.hcs_topic_id);
        XrplAnchor xrpl(cfg.xrpl_account);
        DualAnchor dual(std::move(hcs), std::move(xrpl));
        auto receipt = dual.anchor(att, ok);
        std::cout << "Verifier dual-anchored: " << receipt.combined_hash << "\n";
    } catch (...) {
        std::cout << "Clean proof accepted: false\n";
    }

    try {
        zk.prove("player_001", {0,0,0}, {50.f,0,0}, 16);
        std::cout << "Speedhack rejected: false\n";
    } catch (const InvalidMovement&) {
        std::cout << "Speedhack rejected: true\n";
    }

    ChallengeEngine engine;
    auto ch = engine.issue("some-proof", "anomaly detected");
    std::cout << "Verifier issued challenge: " << ch.challenge_id << "\n";
    std::cout << "Ironwall C++ Verifier shut down\n";
    return 0;
}

// --- live chain demo (runs after existing verifier body if linked) ---
#include "ironwall/chain_submit.hpp"
namespace {
struct ChainDemo {
    ChainDemo() {
        ironwall::ChainConfig cc;
        ironwall::ChainSubmitter sub(cc);
        ironwall::Bytes payload = {0x49,0x57,0x41,0x4c}; // "IWAL"
        auto rec = sub.submit_dual(payload);
        std::cout << "Chain dual-anchor demo combined=" << rec.combined_hash << "\n";
    }
};
// static ChainDemo _chain_demo; // uncomment to auto-run
}
