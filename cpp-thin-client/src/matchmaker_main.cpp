#include "ironwall/ironwall.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    using namespace ironwall;
    std::cout << "Ironwall Matchmaker starting...\n";

    MatchmakerConfig cfg;
    cfg.players_per_match = 2;
    Matchmaker mm(cfg);

    TeeAttestation tee;

    // Simulate 5 players joining
    for (int i = 0; i < 5; ++i) {
        auto att = tee.generate();
        std::string pid = "player_" + std::to_string(i);
        auto ticket = mm.lobby().issue_ticket(pid, att);
        auto sid = mm.enqueue(ticket);
        std::cout << "join " << pid << " session=" << (sid.empty() ? "REJECT" : sid) << "\n";
        auto matches = mm.tick();
        for (auto& m : matches) {
            std::cout << "MATCH " << m.match_id << " ->";
            for (auto& s : m.players) std::cout << " " << s.substr(0, 8);
            std::cout << "\n";
        }
    }

    std::cout << "queue_remaining=" << mm.queue_size()
              << " active_matches=" << mm.active_matches() << "\n";
    std::cout << "Ironwall Matchmaker shut down\n";
    return 0;
}
