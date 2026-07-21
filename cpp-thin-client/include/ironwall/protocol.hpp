#pragma once
#include "types.hpp"
#include "tee.hpp"
#include "zk.hpp"
#include "anchors.hpp"
#include "challenge.hpp"
#include <string>
#include <variant>

namespace ironwall {

struct HelloMsg {
    std::string          player_id;
    std::string          client_version;
    TeeAttestationResult attestation;
};

struct MovementProofMsg {
    ZkMovementProof   proof;
    DualAnchorReceipt anchor;
};

struct ChallengeResponseMsg {
    ChallengeResponse response;
};

struct HeartbeatMsg {
    TimePoint ts;
    Vec3      position;
};

using ClientMessage = std::variant<HelloMsg, MovementProofMsg, ChallengeResponseMsg, HeartbeatMsg>;

struct WelcomeMsg {
    std::string session_id;
    TimePoint   server_time;
};

struct ChallengeMsg {
    Challenge challenge;
};

struct AckMsg {
    std::string            proof_id;
    bool                   accepted = false;
    std::optional<std::string> reason;
};

struct KickMsg {
    std::string reason;
};

using ServerMessage = std::variant<WelcomeMsg, ChallengeMsg, AckMsg, KickMsg>;

} // namespace ironwall
