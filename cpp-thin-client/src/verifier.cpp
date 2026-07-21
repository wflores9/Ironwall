#include "ironwall/ironwall.hpp"
#include "ironwall/ban_store.hpp"
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

    // Moderation demo
    RateLimitConfig rc;
    rc.max_events = 5;
    rc.window_sec = 2.0;
    rc.ban_after_violations = 2;
    rc.ban_duration_sec = 60.0;
    BanStore bans("ironwall_bans.jsonl");
    ModerationEngine mod(rc);
    bans.load_into(mod);

    int allowed = 0, denied = 0;
    for (int i = 0; i < 12; ++i) {
        if (mod.allow("speedy_joe", "proof")) ++allowed;
        else ++denied;
    }
    if (mod.is_banned("speedy_joe")) {
        bans.save_ban("speedy_joe", "rate_limit", rc.ban_duration_sec);
    }
    std::cout << "Moderation demo: allowed=" << allowed
              << " denied=" << denied
              << " banned=" << (mod.is_banned("speedy_joe") ? "yes" : "no")
              << " strikes=" << mod.strike_count("speedy_joe") << "\n";
    std::cout << "Ban store: " << bans.path() << "\n";

        // Lobby handshake demo
    Lobby lobby;
    auto ticket = lobby.issue_ticket("player_001", att);
    auto sid = lobby.open_session(ticket);
    std::cout << "Lobby session=" << sid << " active=" << lobby.active_count()
              << " ticket_ok=" << lobby.validate_ticket(ticket) << "\n";
    lobby.close_session(sid);

    std::cout << "Ironwall C++ Verifier shut down\n";
    return 0;
}
