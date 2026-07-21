#pragma once
#include "types.hpp"
#include "tee.hpp"
#include "zk.hpp"
#include <string>

namespace ironwall {

struct Challenge {
    std::string challenge_id;
    std::string proof_id;
    std::string reason;
    TimePoint   issued_at;
    TimePoint   deadline;
};

struct ChallengeResponse {
    std::string          challenge_id;
    TeeAttestationResult new_attestation;
    ZkMovementProof      new_proof;
    TimePoint            responded_at;
};

class ChallengeEngine {
public:
    Challenge issue(const std::string& proof_id, const std::string& reason) const;
    ChallengeResponse respond(const Challenge& ch,
                              TeeAttestationResult att,
                              ZkMovementProof proof) const;
};

} // namespace ironwall
