#include "ironwall/zk.hpp"
#include "util.hpp"
#include <cmath>
#include <stdexcept>

namespace ironwall {

ZkMovementValidator::ZkMovementValidator(float max_speed) : max_speed_(max_speed) {}

ZkMovementProof ZkMovementValidator::prove(const std::string& player_id,
                                           const Vec3& from,
                                           const Vec3& to,
                                           uint32_t delta_t_ms) const {
    if (delta_t_ms == 0) throw InvalidMovement("delta_t_ms cannot be zero");

    float dist = distance(from, to);
    float dt = delta_t_ms / 1000.f;
    float speed = dist / dt;

    if (speed > max_speed_) {
        throw InvalidMovement("movement speed " + std::to_string(speed) +
                              " exceeds max " + std::to_string(max_speed_) +
                              " (possible speedhack)");
    }

    ZkMovementProof p;
    p.proof_id = util::uuid4();
    p.player_id = player_id;
    p.from = from;
    p.to = to;
    p.delta_t_ms = delta_t_ms;
    p.speed = speed;
    p.timestamp = util::now();

    util::Sha256 h;
    h.update(player_id);
    h.update(reinterpret_cast<const uint8_t*>(&from.x), sizeof(float)*3);
    h.update(reinterpret_cast<const uint8_t*>(&to.x), sizeof(float)*3);
    h.update(reinterpret_cast<const uint8_t*>(&delta_t_ms), sizeof(delta_t_ms));
    h.update(reinterpret_cast<const uint8_t*>(&speed), sizeof(speed));
    p.public_inputs_hash = h.hexdigest();

    util::Sha256 ph;
    ph.update("ironwall-zk-movement-proof-v1");
    ph.update(p.public_inputs_hash);
    p.proof_bytes = ph.digest();

    return p;
}

} // namespace ironwall
