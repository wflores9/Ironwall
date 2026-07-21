#pragma once
#include "types.hpp"
#include "config.hpp"
#include "tee.hpp"
#include "protocol.hpp"
#include <string>

namespace ironwall {

struct Session {
    std::string          session_id;
    std::string          player_id;
    TimePoint            started_at;
    TimePoint            last_heartbeat;
    TeeAttestationResult attestation;
    uint64_t             proofs_submitted = 0;
    uint64_t             challenges_received = 0;
    Vec3                 position;

    static Session create(const Config& cfg, TeeAttestationResult att);
    HeartbeatMsg heartbeat(const Vec3& pos);
    void record_proof();
    void record_challenge();
};

} // namespace ironwall
