#include "ironwall/session.hpp"
#include "util.hpp"

namespace ironwall {

Session Session::create(const Config& cfg, TeeAttestationResult att) {
    Session s;
    s.session_id = util::uuid4();
    s.player_id = cfg.player_id;
    s.started_at = util::now();
    s.last_heartbeat = s.started_at;
    s.attestation = std::move(att);
    return s;
}

HeartbeatMsg Session::heartbeat(const Vec3& pos) {
    last_heartbeat = util::now();
    position = pos;
    return HeartbeatMsg{last_heartbeat, pos};
}

void Session::record_proof() { ++proofs_submitted; }
void Session::record_challenge() { ++challenges_received; }

} // namespace ironwall
