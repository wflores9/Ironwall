#include "util.hpp"
#include "ironwall/c_api.h"
#include "ironwall/ironwall.hpp"
#include <cstring>
#include <string>
#include <memory>

struct ironwall_client {
    ironwall::Config cfg;
    ironwall::TeeAttestation tee;
    ironwall::TeeAttestationResult att;
    ironwall::ZkMovementValidator zk;
    ironwall::DualAnchor anchors;
    ironwall::Session session;
    bool has_att = false;
    bool has_session = false;

    ironwall_client(const char* player, float max_speed)
        : zk(max_speed)
        , anchors(ironwall::HcsAnchor("0.0.123456"), ironwall::XrplAnchor("rIronwallAnchorXXXXXXXXXXXXXXXXXX"))
    {
        cfg.player_id = player ? player : "player_001";
        cfg.max_speed = max_speed;
    }
};

extern "C" {

const char* ironwall_version(void) { return "0.1.0"; }

ironwall_client* ironwall_client_create(const char* player_id, float max_speed) {
    try {
        return new ironwall_client(player_id, max_speed);
    } catch (...) {
        return nullptr;
    }
}

void ironwall_client_destroy(ironwall_client* c) {
    delete c;
}

int ironwall_client_attest(ironwall_client* c, char* out_quote_hash, size_t out_len) {
    if (!c || !out_quote_hash || out_len < 65) return -1;
    try {
        c->att = c->tee.generate();
        c->session = ironwall::Session::create(c->cfg, c->att);
        c->has_att = true;
        c->has_session = true;
        std::snprintf(out_quote_hash, out_len, "%s", c->att.quote_hash.c_str());
        return 0;
    } catch (...) {
        return -2;
    }
}

int ironwall_client_prove_movement(
    ironwall_client* c,
    float from_x, float from_y, float from_z,
    float to_x, float to_y, float to_z,
    uint32_t delta_t_ms,
    char* out_proof_id, size_t proof_id_len,
    char* out_combined_hash, size_t hash_len
) {
    if (!c || !c->has_att || !out_proof_id || !out_combined_hash) return -1;
    try {
        ironwall::Vec3 from{from_x, from_y, from_z};
        ironwall::Vec3 to{to_x, to_y, to_z};
        auto proof = c->zk.prove(c->cfg.player_id, from, to, delta_t_ms);
        auto receipt = c->anchors.anchor(c->att, proof);
        c->session.record_proof();
        std::snprintf(out_proof_id, proof_id_len, "%s", proof.proof_id.c_str());
        std::snprintf(out_combined_hash, hash_len, "%s", receipt.combined_hash.c_str());
        return 0;
    } catch (const ironwall::InvalidMovement&) {
        return -3; // speedhack / invalid
    } catch (...) {
        return -2;
    }
}

int ironwall_client_respond_challenge(
    ironwall_client* c,
    const char* challenge_id,
    char* out_response_id, size_t out_len
) {
    if (!c || !c->has_att || !challenge_id || !out_response_id) return -1;
    try {
        ironwall::ChallengeEngine eng;
        // rebuild a dummy challenge for the stub API
        ironwall::Challenge ch;
        ch.challenge_id = challenge_id;
        ch.proof_id = "unknown";
        ch.reason = "api";
        ch.issued_at = ironwall::util::now();
        ch.deadline = ch.issued_at + std::chrono::seconds(60);

        auto fresh_att = c->tee.generate();
        auto proof = c->zk.prove(c->cfg.player_id, {0,0,0}, {0.01f,0,0}, 50);
        auto resp = eng.respond(ch, fresh_att, proof);
        c->session.record_challenge();
        std::snprintf(out_response_id, out_len, "%s", resp.challenge_id.c_str());
        return 0;
    } catch (...) {
        return -2;
    }
}

} // extern "C"
