#pragma once
#include "types.hpp"
#include <string>
#include <stdexcept>

namespace ironwall {

struct ZkMovementProof {
    std::string proof_id;
    std::string player_id;
    Vec3        from;
    Vec3        to;
    uint32_t    delta_t_ms = 0;
    Bytes       proof_bytes;
    std::string public_inputs_hash;
    TimePoint   timestamp;
    float       speed = 0.f;
};

class ZkMovementValidator {
public:
    explicit ZkMovementValidator(float max_speed);
    ZkMovementProof prove(const std::string& player_id,
                          const Vec3& from,
                          const Vec3& to,
                          uint32_t delta_t_ms) const;
private:
    float max_speed_;
};

class InvalidMovement : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

} // namespace ironwall
