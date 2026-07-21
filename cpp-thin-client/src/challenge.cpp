#include "ironwall/challenge.hpp"
#include "util.hpp"
#include <stdexcept>

namespace ironwall {

Challenge ChallengeEngine::issue(const std::string& proof_id, const std::string& reason) const {
    Challenge c;
    c.challenge_id = util::uuid4();
    c.proof_id = proof_id;
    c.reason = reason;
    c.issued_at = util::now();
    c.deadline = c.issued_at + std::chrono::seconds(30);
    return c;
}

ChallengeResponse ChallengeEngine::respond(const Challenge& ch,
                                           TeeAttestationResult att,
                                           ZkMovementProof proof) const {
    if (util::now() > ch.deadline)
        throw std::runtime_error("challenge deadline exceeded");

    ChallengeResponse r;
    r.challenge_id = ch.challenge_id;
    r.new_attestation = std::move(att);
    r.new_proof = std::move(proof);
    r.responded_at = util::now();
    return r;
}

} // namespace ironwall
