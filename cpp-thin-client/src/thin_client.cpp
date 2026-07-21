#include "ironwall/thin_client.hpp"
#include <iostream>
#include <thread>
#include <chrono>

namespace ironwall {

ThinClient::ThinClient(Config cfg, TeeAttestationResult att, ZkMovementValidator zk, DualAnchor anchors)
    : cfg_(std::move(cfg)), att_(std::move(att)), zk_(std::move(zk)), anchors_(std::move(anchors)) {}

void ThinClient::run() {
    std::cout << "[client] Thin client main loop started\n";
    std::cout << "[client] Attestation quote: " << att_.quote_hash << "\n";

    uint32_t tick_ms = 1000 / std::max(cfg_.tick_rate_hz, 1u);
    for (uint64_t tick = 0; tick < cfg_.demo_ticks; ++tick) {
        Vec3 from = position_;
        Vec3 to{from.x + 0.12f, from.y, from.z + 0.08f};

        try {
            auto proof = zk_.prove(cfg_.player_id, from, to, tick_ms);
            std::cout << "[client] tick=" << tick
                      << " pos=(" << to.x << "," << to.y << "," << to.z << ")"
                      << " speed=" << proof.speed
                      << " proof=" << proof.proof_id << "\n";

            auto receipt = anchors_.anchor(att_, proof);
            std::cout << "[client] anchored combined_hash=" << receipt.combined_hash << "\n";
            position_ = to;
        } catch (const InvalidMovement& e) {
            std::cout << "[client] movement rejected: " << e.what() << "\n";
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(tick_ms));
    }
    std::cout << "[client] Demo loop finished\n";
}

} // namespace ironwall
